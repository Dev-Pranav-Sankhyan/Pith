# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Python 3.11+, mostly standard library (`requirements.txt` only adds Pillow). Run everything from the repo root, because modules import as `core.*` / `pipeline.*`.

```bash
python3 server.py                                  # local site + JSON API on :8000 (PORT env overrides)
python3 -m unittest discover tests                 # full test suite
python3 -m unittest tests.test_foryou              # one test module
python3 -m unittest tests.test_foryou.TestName.test_method   # one test
python3 run_daily.py --dry-run --skip-audio        # full daily pipeline, no LLM/TTS calls
python3 -m pipeline.render_html                    # re-render static pages from brief.sqlite3
python3 -m pipeline.ingest_llm --url <url> --add-to-issue --rebuild   # ingest one story into today's issue
python3 -m pipeline.ingest_seed && python3 -m pipeline.build_issue && python3 -m pipeline.render_html  # cold-start seed
python3 -m pipeline.resolve_predictions due                                   # live forecasts past their date
python3 -m pipeline.resolve_predictions resolve <id> --status correct|wrong|void --evidence <url> --by "<name>" [--note "..."]
python3 -m pipeline.resolve_predictions draft <id> --evidence <url>          # LLM-suggested verdict; records nothing
python3 -m pipeline.tune_scoring [--apply]                                    # weights vs resolved outcomes (needs 20)
python3 -m core.cluster_eval                                                  # clustering precision/recall on the gold set
python3 -m pipeline.email_edition                                             # public/email/<date>.html + .txt
```

Video (Remotion, in `video/`): `npm start` (preview), `npm run build` (renders `out/pith-brief.mp4`).

There is no linter or formatter configured.

## Architecture

The site has two halves that share a server and front-end shell but use **separate SQLite databases**:

1. **Daily Brief** (`brief.sqlite3`): an LLM-drafted daily issue of 5 cards plus "Safely Ignore Today", each card carrying a falsifiable prediction.
   - Flow (`pipeline/orchestrate_daily.py`, entry `run_daily.py`): `core/sources.py` collects candidates → `pipeline/ingest_llm.py` asks the LLM (`core/llm.py`, prompts in `core/prompts.py`) for 0–100 factor ratings plus a card draft → `core/scoring.py` takes the weighted sum, subtracts penalties, and applies the threshold (60, or 78 for "High") → `core/verification.py` drops any claim whose `quoted_span` isn't a substring of the fetched source text → `core/db.py` stores the issue → `pipeline/build_issue.py` writes `feed.json`/`rss.xml` → `pipeline/render_html.py` writes the HTML → `pipeline/audio_brief.py` makes ElevenLabs audio in `public/audio/`.
   - LLM provider is picked by `--provider` / `PITH_LLM_PROVIDER` (gemini, openai, anthropic, ollama, simulated). `auto` and `--dry-run` fall back to the simulated provider, so the pipeline runs without API keys.
   - `core/scoring.py` loads `scoring_weights.json` (written by `pipeline/tune_scoring.py`) if present and valid, else `DEFAULT_WEIGHTS`. Tune only on forecast outcomes, never on clicks/saves.
   - `core/llm.py` providers use raw HTTP (stdlib only). The Anthropic one defaults to `claude-opus-5-5`, sends no sampling params, joins only `text` blocks (responses start with thinking blocks) and uses `fallbacks: "default"`.
   - `pipeline/build_issue.py` also writes the email edition (`pipeline/email_edition.py`); set `PITH_SITE_URL` to change links.
   - `core/ledger.py` computes Brier score, hit rate and Brier skill score over resolved **live** predictions only.
   - **Ledger integrity rules (do not weaken):** predictions have `provenance` `live` or `illustrative`; illustrative ones (hand-written examples, e.g. `hist-pred-*`) are never counted in any score. Resolutions go only through `Database.record_resolution` (named reviewer, evidence for correct/wrong) into the append-only `prediction_resolutions` table; triggers block UPDATE/DELETE there and block edits to forecast fields after the publication day. Never write `status` on `predictions` directly, never use `INSERT OR REPLACE` on `predictions`, and never fabricate a forecast, track-record number or crowd figure in a renderer.
   - Schema changes for `brief.sqlite3` are appended to `Database.MIGRATIONS` (numbered, tracked in `schema_version`); never edit a shipped migration.
2. **For You** (`foryou.sqlite3`, schema in `core/newsfeed.py`): a general-news personalized feed.
   - `core/newsfeed.py` pulls about 22 RSS feeds. `server.py` runs it in a daemon thread every `PITH_REFRESH_MINUTES`. When offline it seeds `core/demo_news.py`.
   - `core/clustering.py` merges multi-outlet coverage. Its `MATCH_THRESHOLD` is calibrated on `tests/fixtures/cluster_gold.json`; run `python3 -m core.cluster_eval` before changing matching, and keep precision ≥ 0.95.
   - `core/textfeatures.py` turns each article into rule-based topics, TF-IDF keywords, capitalized-phrase entities, and its publisher. It deliberately uses no ML models.
   - `core/recommender.py` learns per-user affinities from events (half-life decay) and ranks by `confidence*personal + (1-confidence)*baseline`, then applies an MMR re-rank, Thompson-sampling exploration slots, and a per-item explanation. The `CORPUS` singleton caches features in memory and reloads when the article count or latest fetch time changes.
   - `core/auth.py`: PBKDF2 passwords, session token in an HttpOnly cookie, with only the token's SHA-256 stored.
   - `core/your5.py` is the bridge between the two halves: it picks a personal "Your 5" from the brief using inferred role and affinities (`/api/your5`, `/api/digest`).

`server.py` is a stdlib `SimpleHTTPRequestHandler` serving `public/`, with hand-routed APIs: `/api/issue`, `/api/ledger`, `/api/score`, and the For You routes (`/api/me|feed|profile|your5|digest|events|onboard|auth/*|refresh`). POST bodies must be JSON; that content-type check is the CSRF guard, so keep it. Pretty paths (`/ledger`, `/foryou`, …) map to the `.html` files. Daily News, Ledger, Archive, Patterns and About are public (`PUBLIC_PAGES`); only For You is login-gated (`MEMBER_PAGES`). Don't add a client-side login redirect: on GitHub Pages there is no API, so it would lock everyone out. Reader forecast votes: `POST /api/vote` (login) and `GET /api/votes?card_id=` (`core/votes.py`, `forecast_votes` table). Login/signup, other POSTs and `/api/refresh` are rate limited per IP (`core/ratelimit.py`). `/healthz` returns `{"ok": true}`. Decommissioned paths (`/horizon`, `/bounty`, `/matrix`, `/economics`, `/terminal`) are handled explicitly.

### Generated vs hand-written front-end files

- **Generated, so edit the Python renderer instead:** `public/index.html`, `ledger.html`, `patterns.html` (`pipeline/render_html.py`), `archive.html` and `about.html` (`pipeline/render_extended.py`), and `feed.json`/`rss.xml`. The shared global nav lives in `render_extended.get_nav_html`.
- `style.css` has the global `*` reset commented out on purpose (see the note there): the site was tuned without it.
- **Hand-written:** `public/app.js` (brief UI, lens switching, Beat-the-Brief ELO, Web Audio sounds), `style.css`, `foryou.html`, `foryou.js`, `foryou.css`.

## Repo conventions

- `.github/workflows/daily_brief.yml` runs `run_daily.py` daily at 05:00 UTC. It **commits `brief.sqlite3` and `public/` back to the branch** (`chore(daily): ... [skip ci]`) and deploys `public/` to GitHub Pages. Expect bot commits on `main`, and pull before editing generated files.
- `.github/workflows/daily_video_pipeline.yml` runs the Whisper alignment (`pipeline/video_align.py`), the Remotion render, and `pipeline/auto_publish.py`. `auto_publish` defaults to `--dry-run`.
- Env vars used: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` (+`OPENAI_BASE_URL`), `GEMINI_API_KEY`, `GROQ_API_KEY`, `ELEVENLABS_API_KEY`, `PITH_LLM_PROVIDER`, `PITH_REFRESH_MINUTES`, `PITH_SECURE_COOKIES=1` (adds `Secure` to cookies), and the social publishing tokens (`YOUTUBE_API_TOKEN`, `X_API_KEY`, `LINKEDIN_ACCESS_TOKEN`).
- `PROJECT_CONTEXT.md` is the product chronicle. Update its phase table when adding or removing a destination.
