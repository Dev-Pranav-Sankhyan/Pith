# Pith · High-Signal Tech Intelligence

> Ultra-minimalist daily intelligence web app filtering tech news down to 5 falsifiable events that alter architectures, unit economics, or platform moats. Built with the *Working Memory Lab* luxury editorial aesthetic, interactive calibration games, zero heavy WebGL dependencies, and sub-second load times.

---

## What is Pith?

Most tech feeds monetize anxiety, clickbait, and FOMO. **Pith** does the opposite:
1. **Lowpass Noise-to-Signal Filter**: Strips out PR releases, synthetic benchmarks, and cosmetic UI drama.
2. **Plain English + Tailored Technical Lenses**: "What Happened" and "Why It Matters" are written in crisp, jargon-free English. Deep technical specifics are strictly isolated inside **Developer**, **Founder**, and **Investor** lenses.
3. **Public Accountable Predictions**: Every item carries a falsifiable prediction with exact resolution criteria, tracked in a Brier score ledger with post-mortems for wrong calls.
4. **"Beat the Brief" (Reader vs. Site Calibration)**: A 30-second daily forecasting game where readers log their probability assessments and earn a live Calibration ELO rating.
5. **The "Contrarian Multiplier"**: Anyone who bets against dominant consensus—and wins—earns 2x ELO points, rewarding independent strategic thinking over herd behavior.
6. **"Zero-FOMO" Completion**: When you finish the issue, there is no infinite scroll or algorithmic rabbit hole. The briefing locks with *"Briefing complete. Go build."*

---

## 4 Crazy Micro-Animations & Tactile Interactions (<1s Load, Zero WebGL)

1. **The "Noise-to-Signal" Compression (Lowpass)**:
   - On first landing (or via `↻ Lowpass`), a chaotic cloud of 20+ frantic tech buzzwords and hype posts flutters across the screen.
   - A razor-sharp neon laser filter line sweeps smoothly down in 0.8s, vaporizing the noise with a synthetic ion sweep sound and snapping the 5 high-signal Pith cards into sharp focus.
   - Stored in `sessionStorage` so returning readers are never slowed down. Replayable on demand.

2. **The "Split-Flap" Role Morph**:
   - Toggling between **Developer** → **Founder** → **Investor** keeps the headline and "What Happened" frozen.
   - The Impact and Action directives dynamically scramble and flip character-by-character like an airport mechanical departure board over 220ms, accompanied by a rapid relay audio click.
   - Border glows dynamically shift color:
     - **Terminal Green** (`#246B52`) for Developer
     - **Crisp Amber** (`#D97706`) for Founder
     - **Electric Blue** (`#2563EB`) for Investor

3. **The "On-Record" Ledger Stamp**:
   - Tapping *Higher / Agree / Lower* on Beat the Brief doesn't just toggle a button:
   - A mechanical notary stamp (`SEALED #HASH · TIME`) slams onto the card with a 2-pixel micro-shake (`stampShake`) and a deep mechanical thud + metallic snap.
   - Instantly calculates Contrarian Multipliers and updates your live ELO rating in the Crown header.

4. **The "Safely Ignore" Shredder**:
   - In the *Safely Ignore Today* section, clicking **"Clear the Noise"** triggers a paper-shredder dissolve animation that vaporizes distraction stories, leaving a peaceful, serene state: *"Noise obliterated. Focus preserved."*

5. **Pure Web Audio Synthesizer**:
   - Zero audio files, zero HTTP requests, and zero latency.
   - Generates mechanical switch snaps, theme shutters, split-flap relays, notary stamp slams, and laser sweeps directly in browser memory using the Web Audio API.

---

## Directory Structure

```
├── schemas/
│   ├── card.schema.json         # JSON schema for cards
│   └── issue.schema.json        # JSON schema for daily issues
├── core/
│   ├── models.py                # Dataclasses & validation logic (DailyIssue, Card, RoleView)
│   ├── db.py                    # SQLite repository & schema
│   ├── scoring.py               # 6-factor weighted scoring engine + penalty deduction
│   ├── verification.py          # Claim quote-check & prediction validation
│   ├── ledger.py                # Brier score & calibration math
│   └── patterns_data.py         # Curated architectural dynamics & base rates
├── pipeline/
│   ├── ingest_seed.py           # Seed script for 5 high-signal cards & historical ledger
│   ├── build_issue.py           # RSS 2.0 & JSON Feed generator
│   └── render_html.py           # Static site generator for Pith pages
├── public/
│   ├── index.html               # Pith Daily Intelligence Brief
│   ├── ledger.html              # Prediction Ledger & Calibration
│   ├── patterns.html            # Pattern Library & Mental Models
│   ├── style.css                # Working Memory Lab design system + animations
│   ├── app.js                   # Client engine, ELO system, sound synth & animations
│   ├── rss.xml                  # RSS 2.0 Feed
│   └── feed.json                # JSON Feed
├── tests/
│   └── test_model.py            # Unit test suite
├── server.py                    # Local server & API
└── brief.sqlite3                # SQLite database
```

---

## Quickstart

### 1. Run Unit Tests
```bash
python3 -m unittest discover tests
```

### 2. Ingest Seed Data & Build All Pages
```bash
python3 -m pipeline.ingest_seed && python3 -m pipeline.build_issue && python3 -m pipeline.render_html
```

### 3. Master Daily Autonomous Publishing (Zero-Touch)
Run the entire end-to-end publishing pipeline in a single command:
```bash
# 1. Live Run (Pulls from 7 feeds, scores signal, generates 4-role briefs, synthesizes studio audio)
python3 run_daily.py

# 2. Simulation / Dry-Run (Runs complete pipeline without external LLM API calls)
python3 run_daily.py --dry-run

# 3. Fast Build (Rebuilds cards, predictions, and HTML while skipping voice audio generation)
python3 run_daily.py --skip-audio
```

### 4. Fully Automated GitHub Action (Daily at 05:00 UTC)
Pith includes an automated daily workflow in `.github/workflows/daily_brief.yml`:
- **Schedule**: Automatically runs every day at 05:00 UTC (10:30 AM IST / 01:00 AM EST).
- **Manual Trigger**: Tap "Run workflow" in GitHub Actions with optional flags (`dry_run`, `skip_audio`).
- **Required Repository Secrets** (add under *Settings > Secrets and variables > Actions*):
  - `ELEVENLABS_API_KEY`: For high-realism voice synthesis.
  - `GEMINI_API_KEY` (or `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`): For automated signal scoring and 4-lens drafting.
- Automatically commits updated SQLite database, static HTML, feeds, and mastered audio files back to `main`, and deploys the About page (the only page open without signing in) to GitHub Pages. Everything else is served by `server.py` to signed-in readers.

### 5. Start Development Server
You can ingest any raw article, announcement, or URL with an LLM. It automatically scores signal (0-100), drafts structured JSON, verifies quoted spans, and updates your issue:

```bash
# 1. Ingest via Google Gemini (Default)
export GEMINI_API_KEY="your-gemini-key"
python3 -m pipeline.ingest_llm --url "https://github.com/vllm-project/vllm/releases/tag/v0.7.0" --add-to-issue --rebuild

# 2. Ingest via OpenAI or Groq / DeepSeek
export OPENAI_API_KEY="your-openai-key"
python3 -m pipeline.ingest_llm --url "https://news.ycombinator.com/item?id=..." --provider openai --add-to-issue --rebuild

# 3. Ingest via Anthropic Claude
export ANTHROPIC_API_KEY="your-anthropic-key"
python3 -m pipeline.ingest_llm --url "https://..." --provider anthropic --add-to-issue --rebuild

# 4. Ingest 100% locally via Ollama (Free, offline, zero API keys)
python3 -m pipeline.ingest_llm --url "https://..." --provider ollama --model "llama3.2" --add-to-issue --rebuild

# 5. Offline Dry-Run Simulation (Testing without API keys)
python3 -m pipeline.ingest_llm --dry-run
```

### 4. Start Development Server
```bash
python3 server.py
```
Open `http://localhost:8000` in your browser.
