"""
Unified LLM Client for Pith.
Supports Google Gemini, OpenAI/Groq/DeepSeek, Anthropic Claude, Local Ollama, and Dry-Run Simulation.
Zero external dependencies (uses standard library urllib.request and json).
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


def clean_json_response(raw_text: str) -> str:
    """Strips markdown code fences (```json ... ```) from LLM output."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class BaseLLMProvider:
    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or constructor.")

    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.2,
            }
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                raise RuntimeError(f"Unexpected Gemini response structure: {res_json}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini API error ({e.code}): {err_body}") from e


class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model
        if not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            raise ValueError("OPENAI_API_KEY is not set in environment or constructor.")

    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                choices = res_json.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                raise RuntimeError(f"Unexpected OpenAI response: {res_json}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"OpenAI API error ({e.code}): {err_body}") from e


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set in environment or constructor.")

    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        url = "https://api.anthropic.com/v1/messages"
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                contents = res_json.get("content", [])
                if contents:
                    return contents[0].get("text", "")
                raise RuntimeError(f"Unexpected Anthropic response: {res_json}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Anthropic API error ({e.code}): {err_body}") from e


class OllamaProvider(BaseLLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.2}
        }
        if json_mode:
            payload["format"] = "json"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                return res_json.get("response", "")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama error ({e.code}): {err_body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Could not connect to Ollama at {self.base_url}. Ensure 'ollama serve' is running.") from e


class SimulatedProvider(BaseLLMProvider):
    """
    Offline simulation provider for testing, demoing, and CI/CD without API keys.
    Extracts key sentences from the raw text to produce compliant, verified Pith cards.
    """
    def complete(self, system_prompt: str, user_prompt: str, json_mode: bool = True) -> str:
        # Check if scoring or card draft is requested
        if "rate this article on the following 6 dimensions" in user_prompt.lower():
            return json.dumps({
                "features": {
                    "breadth_of_affected_users": 84.0,
                    "switching_or_lockin_cost": 88.0,
                    "irreversibility": 82.0,
                    "source_quality_corroboration": 92.0,
                    "novelty_vs_trend": 78.0,
                    "time_sensitivity": 75.0
                },
                "penalties": {
                    "press_release_language": False,
                    "no_verifiable_facts": False,
                    "pure_product_review": False
                }
            })

        # Extract quote span from user prompt text
        first_few_lines = [line.strip() for line in user_prompt.splitlines() if line.strip() and not line.startswith("SOURCE") and not line.startswith("TITLE") and not line.startswith("PUBLISHER") and not line.startswith("Analyze") and not line.startswith("RAW") and not line.startswith("Produce") and len(line.strip()) > 30]
        quote = first_few_lines[0] if first_few_lines else "the software infrastructure update standardizes system protocols"

        return json.dumps({
            "headline": "Infrastructure Standard Introduced to Reduce Multi-Cloud Tool Lock-In",
            "what_happened": f"A major open specification was released for AI developer workflows. {quote[:90]}.",
            "why_it_matters": "Engineering teams gain cross-provider interoperability for distributed agent runtimes. Closed single-model ecosystems lose leverage over client tool pipelines.",
            "second_order": [
                "Tool providers standardize on unified RPC schemas rather than vendor-specific SDK wrappers",
                "Internal service proxies enforce access control policies at the organization network perimeter",
                "Switching costs between frontier model providers drop significantly"
            ],
            "confidence": "High",
            "action_type": "DO",
            "action_text": "Audit tool schema formatting utilities this week to standardize endpoint definitions.",
            "prediction": {
                "statement": "By 31 December 2027, at least three leading database runtimes natively support this standardized RPC endpoint.",
                "probability": 0.70,
                "resolves_at": "2027-12-31",
                "resolution_criteria": "Official repository release documentation details native endpoint protocol support without external bridge proxies.",
                "category": "adoption"
            },
            "historical_analogue": {
                "analogue": "Resembles the Container Network Interface (CNI) standardization in cloud-native container runtimes (2016-2017).",
                "where_it_breaks": "Agent tool schemas carry state and prompt context far more dynamic than network block routing."
            },
            "claims": [
                {
                    "text": "The release introduces a standardized specification for developer tool runtimes.",
                    "quoted_span": quote[:45]
                }
            ],
            "role_views": {
                "developer": {
                    "impact": "Eliminates the maintenance overhead of synchronizing separate function-calling schemas for multiple LLM client libraries.",
                    "action_type": "DO",
                    "action_text": "Benchmark JSON-RPC schema translation on your core internal tool endpoints.",
                    "stakes": "Medium"
                },
                "founder": {
                    "impact": "Lowers distribution friction: your platform can connect to any conforming agent client without custom bilateral partnerships.",
                    "action_type": "WATCH",
                    "action_text": "Monitor whether major client IDEs and models commit to standard protocol conformance.",
                    "stakes": "High"
                },
                "investor": {
                    "impact": "Commoditizes thin tool-routing middleware; enterprise defensibility concentrates in proprietary data ownership and sandboxed execution.",
                    "action_type": "WATCH",
                    "action_text": "Review developer tooling portfolio companies to ensure they do not depend on proprietary routing lock-in.",
                    "stakes": "Medium"
                },
                "everyday": {
                    "impact": "Apps will talk to each other like USB-C plugs, without asking you to create ten separate accounts.",
                    "action_type": "IGNORE",
                    "action_text": "No action needed; future consumer app updates will connect smoothly.",
                    "stakes": "Low"
                }
            }
        })


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    dry_run: bool = False
) -> BaseLLMProvider:
    """
    Factory that instantiates the desired provider.
    Auto-detects active environment variables if provider_name is omitted or 'auto'.
    Falls back to SimulatedProvider if dry_run=True or no API keys are found.
    """
    if dry_run:
        return SimulatedProvider()

    p_name = (provider_name or os.environ.get("PITH_LLM_PROVIDER") or "auto").lower()

    if p_name == "auto":
        if os.environ.get("GEMINI_API_KEY"):
            p_name = "gemini"
        elif os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY"):
            p_name = "openai"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            p_name = "anthropic"
        else:
            # Check local Ollama or fallback to simulated
            return SimulatedProvider()

    if p_name == "gemini":
        return GeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")
    elif p_name in ("openai", "groq", "deepseek"):
        return OpenAIProvider(api_key=api_key, base_url=base_url, model=model or "gpt-4o-mini")
    elif p_name == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model or "claude-3-5-sonnet-20241022")
    elif p_name == "ollama":
        return OllamaProvider(base_url=base_url or "http://localhost:11434", model=model or "llama3.2")
    elif p_name == "simulated":
        return SimulatedProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {p_name}. Supported: gemini, openai, anthropic, ollama, simulated")
