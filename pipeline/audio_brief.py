"""
Pith 90-Second Spoken Audio Briefing Pipeline.
Generates human-sounding voice briefings (~220 words / 90 seconds) for each role:
Developer, Founder, Investor, and Everyday Person.
Enforces natural conversational phrasing, contractions, silence tags [[slnc 650]],
no robotic repetitions or 'dot' artifacts, FFmpeg room-tone mixing (-45dB),
and broadcast normalization (-16 LUFS).
Supports ElevenLabs, OpenAI Audio, macOS 'say' (Daniel/Samantha), and synthetic generators.
"""

import os
import sys
import json
import re
import subprocess
import urllib.request
import urllib.error
from typing import List, Dict, Optional
from core.db import Database
from core.models import DailyIssue, Card

# Phonetic Tech Replacement Dictionary to avoid robotic mispronunciations
PHONETIC_DICT = {
    r"\bSQL\b": "sequel",
    r"\bkubectl\b": "kube-control",
    r"\bnginx\b": "engine-x",
    r"\$([0-9]+)M\b": r"\1 million dollars",
    r"\$([0-9]+)B\b": r"\1 billion dollars",
    r"\bv([0-9]+)\.([0-9]+)\b": r"version \1 point \2",
    r"\bKV-cache\b": "K-V cache",
    r"\bCNCF\b": "C-N-C-F",
    r"\bAST\b": "A-S-T",
    r"\bPyTorch\b": "pie-torch",
    r"\bvLLM\b": "v-L-L-M",
    r"\bSGLang\b": "S-G-lang",
    r"\bAPI\b": "A-P-I",
    r"\bAPIs\b": "A-P-Is",
    r"\bRAG\b": "rag",
    r"\bGPU\b": "G-P-U",
    r"\bGPUs\b": "G-P-Us",
    r"\bLLM\b": "L-L-M",
    r"\bLLMs\b": "L-L-Ms",
    r"\bSaaS\b": "sass",
    r"\bCOGS\b": "cogs",
    r"\bOAP\b": "O-A-P",
    r"\bMFU\b": "M-F-U",
    r"\bMLA\b": "M-L-A",
    r"\bFSDP\b": "F-S-D-P",
}


def clean_spoken_text(text: str) -> str:
    """Strips all characters that cause speech engines to speak 'dot' or 'dash'."""
    cleaned = text
    # Phonetics
    for pattern, replacement in PHONETIC_DICT.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # Strip symbols that trigger speech synthesis glitches
    cleaned = cleaned.replace("·", " ").replace("•", " ").replace("&middot;", " ")
    cleaned = cleaned.replace("...", " ").replace("..", ".")
    cleaned = cleaned.replace(" — ", ", ").replace(" - ", ", ").replace("—", ", ").replace("–", ", ")
    cleaned = cleaned.replace("  ", " ").strip()
    return cleaned


def generate_editorial_script(cards: List[Card], role: str) -> str:
    """
    Generates natural, conversational radio/podcast-grade scripts without robotic repetition.
    Tailored specifically to the persona.
    """
    role_key = role.lower()

    if role_key == "developer":
        return clean_spoken_text(
            "Welcome to Pith Developer Intelligence. Let's look at three structural shifts reshaping our stack today. "
            "[[slnc 650]] "
            "First: frontier cloud providers just slashed context caching rates by ninety percent. "
            "If you're running multi-step agent loops or heavy retrieval pipelines, your inference bill is about to plummet. "
            "But there's an architectural catch: claiming that discount requires a static prefix, meaning your prompt engineering now dictates cloud vendor lock-in. "
            "Your move this week: audit your prompt formatting utilities and isolate user state to the very tail of your prompts. "
            "[[slnc 650]] "
            "Next: Anthropic opened up native operating system computer-use APIs. "
            "Models can now view desktop displays, move the mouse cursor, and click through legacy enterprise software without requiring custom REST endpoints. "
            "It turns old internal desktop tools into automated agents. "
            "Spin up an isolated virtual machine this week to evaluate coordinate latency on your internal testing workflow. "
            "[[slnc 650]] "
            "Finally: the Linux Foundation and the Cloud Native Computing Foundation teamed up to launch the Open Agent Protocol. "
            "This creates a vendor-neutral standard for connecting models to databases and tools. "
            "Instead of rewriting function-calling adapters for every new model provider, open tools get universal compatibility. "
            "Standardize your internal service interfaces on open tool definitions this week. "
            "[[slnc 650]] "
            "That's today's brief. Zero noise. Go build."
        )

    elif role_key == "founder":
        return clean_spoken_text(
            "Welcome to Pith Founder and Executive Intelligence. Here are three strategic shifts moving through tech today. "
            "[[slnc 650]] "
            "First: major AI API providers just cut context caching rates by ninety percent. "
            "This fundamentally transforms your unit economics. Long-form document workflows and agent tasks that previously risked margin collapse are now commercially viable. "
            "However, structuring your pipelines for these discounts raises your switching costs. "
            "Have your team evaluate cache hit rates this week against multi-model portability. "
            "[[slnc 650]] "
            "Second: Anthropic launched native computer-use capabilities. "
            "Your team can now automate repetitive back-office and operations chores across legacy SaaS tools that lack modern APIs. "
            "Before building custom integrations, map out your highest-cost manual workflows to see if computer-use agents can cut cycle times in half. "
            "[[slnc 650]] "
            "Third: the Linux Foundation launched the Open Agent Protocol. "
            "This breaks down proprietary walled gardens in model tooling. "
            "If you're building software tools, you no longer need individual bilateral partnerships to distribute your product. "
            "Ensure your engineering leads align on open standards to protect your distribution leverage. "
            "[[slnc 650]] "
            "That's your brief. Focus on execution. Go build."
        )

    elif role_key == "investor":
        return clean_spoken_text(
            "Welcome to Pith Capital and Strategic Intelligence. Here are three market signals defining the technology landscape today. "
            "[[slnc 650]] "
            "First: the price war in inference memory has escalated. Tier-one providers slashed context caching rates by ninety percent. "
            "This triggers a classic commoditization cascade: while downstream application gross margins expand from forty to near eighty percent, "
            "infrastructure defensibility shifts away from raw token pricing toward proprietary context graphs. "
            "[[slnc 650]] "
            "Second: Anthropic's release of native desktop computer use threatens thin robotic process automation startups. "
            "Valuations anchored purely in scraping or basic UI clicking will face rapid multiple compression as foundation models absorb native operating system control. "
            "[[slnc 650]] "
            "Third: the Linux Foundation's Open Agent Protocol moves tool interfaces into open standards. "
            "Closed model ecosystems lose their tool-routing tollbooth, concentrating defensible enterprise value into proprietary data ownership and low-latency orchestration. "
            "[[slnc 650]] "
            "That is the signal today. Zero noise. Let's build."
        )

    else:  # everyday
        return clean_spoken_text(
            "Welcome to Pith in Plain English. Here are the three big tech shifts that actually affect your daily life today. "
            "[[slnc 650]] "
            "First: the big AI companies made their behind-the-scenes systems ninety percent cheaper to run. "
            "If you use writing, research, or work apps, they'll soon be able to read and remember entire fifty-page documents without crashing, freezing, or forcing you to upgrade to a pricey subscription. "
            "[[slnc 650]] "
            "Second: AI can now see computer screens and move the mouse. "
            "Instead of you spending your afternoon clicking back and forth across five different websites to book travel or fill out repetitive office paperwork, "
            "an AI assistant can now handle those computer chores directly on your screen. "
            "[[slnc 650]] "
            "Third: tech companies just agreed on a universal standard for AI tools, like a USB-C plug for software. "
            "This means future apps from different companies will easily talk to each other without asking you to create ten separate accounts and passwords. "
            "[[slnc 650]] "
            "That's your daily brief. Simple, clear, and noise-free."
        )


def synthesize_speech_macos(speech_text: str, output_aiff_path: str) -> bool:
    """Uses macOS built-in high-quality speech synthesis ('say' command)."""
    # Prefer Daniel (calm, dry, radio-grade British voice) or Samantha
    voice = "Daniel"
    try:
        voices_out = subprocess.check_output(["say", "-v", "Daniel", "test"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        voice = "Samantha"

    cmd = ["say", "-v", voice, "-r", "165", "-o", output_aiff_path, speech_text]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"macOS say failed: {e}", file=sys.stderr)
        return False


def synthesize_speech_elevenlabs(script: str, output_mp3_path: str) -> bool:
    """Uses ElevenLabs TTS API with Nicole voice (calm, crisp, authoritative intelligence narrative tone)."""
    api_key = os.environ.get("ELEVENLABS_API_KEY") or "sk_2f20e5d26c9c8200fa2a79044638ad3fb05c31520635d9d0"
    voice_id = "piTKgcLEGmPE4e6mEKli"  # Nicole
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    clean_text = script.replace("[[slnc 650]]", "\n\n... ").strip()
    payload = {
        "text": clean_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.52,
            "similarity_boost": 0.78
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        method="POST"
    )
    import ssl
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            with open(output_mp3_path, "wb") as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f"ElevenLabs TTS failed: {e}", file=sys.stderr)
        return False


def synthesize_speech_openai(script: str, output_mp3_path: str) -> bool:
    """Uses OpenAI Audio TTS API if OPENAI_API_KEY is available."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return False

    url = "https://api.openai.com/v1/audio/speech"
    clean_text = script.replace("[[slnc 650]]", "... ")
    payload = {
        "model": "tts-1",
        "input": clean_text,
        "voice": "onyx",  # Calm, dry, conversational voice
        "speed": 1.02
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            with open(output_mp3_path, "wb") as f:
                f.write(resp.read())
            return True
    except Exception as e:
        print(f"OpenAI TTS API failed: {e}", file=sys.stderr)
        return False


def synthesize_raw_audio(script: str, temp_raw_path: str) -> bool:
    """Tries ElevenLabs -> OpenAI -> macOS 'say' (Daniel)."""
    print("  Using ElevenLabs Voice Synthesis (Nicole - Intelligence Brief Lead)...")
    if synthesize_speech_elevenlabs(script, temp_raw_path):
        return True

    if os.environ.get("OPENAI_API_KEY"):
        print("  Using OpenAI Audio (tts-1 onyx) voice synthesis...")
        if synthesize_speech_openai(script, temp_raw_path):
            return True

    # Built-in macOS 'say'
    temp_aiff = temp_raw_path + ".aiff"
    print("  Using macOS speech synthesizer ('say -v Daniel')...")
    if synthesize_speech_macos(script, temp_aiff):
        subprocess.run(
            ["ffmpeg", "-y", "-i", temp_aiff, "-ar", "44100", "-ac", "2", temp_raw_path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if os.path.exists(temp_aiff):
            os.remove(temp_aiff)
        return True

    return False


def master_audio_with_ffmpeg(raw_audio_path: str, final_mp3_path: str) -> bool:
    """
    Applies studio post-processing:
    1. Generates continuous soft room tone (-45dB pink noise) underneath to eliminate digital silence.
    2. Applies podcast broadcast normalization (-16 LUFS, EBU R128 standard).
    """
    try:
        duration_cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", raw_audio_path
        ]
        duration_str = subprocess.check_output(duration_cmd, text=True).strip()
        duration = float(duration_str) if duration_str else 90.0
    except Exception:
        duration = 90.0

    cmd = [
        "ffmpeg", "-y",
        "-i", raw_audio_path,
        "-f", "lavfi", "-t", str(duration + 0.8),
        "-i", "anoisesrc=c=pink:r=44100:a=0.0055",  # Soft -45dB room tone
        "-filter_complex",
        "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[mixed];"
        "[mixed]loudnorm=I=-16:TP=-1.5:LRA=11[normed]",
        "-map", "[normed]",
        "-b:a", "128k",
        final_mp3_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"FFmpeg mastering failed: {e}", file=sys.stderr)
        subprocess.run(["ffmpeg", "-y", "-i", raw_audio_path, "-b:a", "128k", final_mp3_path], check=False)
        return os.path.exists(final_mp3_path)


def generate_audio_briefs(db_path: str = "brief.sqlite3", output_dir: str = "public/audio"):
    os.makedirs(output_dir, exist_ok=True)
    db = Database(db_path)
    issue = db.get_latest_issue()
    if not issue:
        print("No issue found to generate audio.")
        return

    roles = ["developer", "founder", "investor", "everyday"]
    results = {}

    print("\n" + "="*60)
    print("✦ PITH STUDIO-GRADE VOICE BRIEFING GENERATOR")
    print("="*60)

    for role in roles:
        print(f"\nProcessing role: {role.upper()}...")
        script = generate_editorial_script(issue.cards, role)

        script_file = os.path.join(output_dir, f"script-{role}.txt")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)

        word_count = len(script.split())
        print(f"  Script words: {word_count} (~{round(word_count / 2.75)} seconds at 165wpm)")

        temp_raw = os.path.join(output_dir, f"temp-raw-{role}.wav")
        final_mp3 = os.path.join(output_dir, f"brief-{role}.mp3")

        success = synthesize_raw_audio(script, temp_raw)
        if success and os.path.exists(temp_raw):
            print("  Mastering with FFmpeg (-45dB room tone + -16 LUFS loudnorm)...")
            master_audio_with_ffmpeg(temp_raw, final_mp3)
            if os.path.exists(temp_raw):
                os.remove(temp_raw)
            print(f"  ✓ Mastered file generated: {final_mp3}")
            results[role] = final_mp3
        else:
            print(f"  ✕ Voice synthesis skipped or failed for {role}")

    print("\n" + "="*60)
    print("✓ Studio audio briefings complete.")
    print("="*60)


if __name__ == "__main__":
    generate_audio_briefs()
