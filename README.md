# VoiceBridge AI

A local, synthetic customer → sales → product → engineering → customer prototype with evidence-preserving handoffs. The current development LLM is Ollama `qwen3:4b`. Gnani Prisma v3.0 REST and Timbre v3.0 have returned actual outputs; Batch diarization verification remains pending.

## Run locally

Requirements: Python 3.11+, Node.js 20.9+, pnpm, FFmpeg/ffprobe and running Ollama.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
.venv/bin/python tools/run_local.py
```

Open http://localhost:3000 (API docs: http://localhost:8000/docs). On this Codex desktop the launcher detects bundled Node. Stop an existing launcher with Ctrl-C before restarting it after backend changes. `--dev` enables the frontend development build with polling.

Copy `.env.example` to `.env` only if `.env` does not already exist. Keep credentials server-side. Current local settings:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

`GNANI_API_KEY_ID` enables speech calls. The optional hosted adapter uses `LLM_PROVIDER=openai`, `LLM_API_KEY` and `LLM_MODEL`. Evon is not currently installed or used; a future compatible Ollama model can be selected by its installed name and must pass fresh validation. No local LLM API key is needed for Ollama.

## Guided workflow

Follow **Conversation → Sales Copilot → Requirements → Engineering → Customer response**. Evidence and review history remain available throughout. Each screen exposes the appropriate local demo-role actions directly.

Start with the unbranded marketplace cold-start example from the latest video, or the original device-lifecycle scenario. Upload/record audio, paste turns or start from a brief. Review speakers, ask source-grounded AI questions, adapt a pitch, accept scope, approve engineering assessments, audit the exact customer draft and generate approved Timbre audio.

Academy has three personas per product, persisted history, transparent baseline scores and actual AI coaching. Insights shows stored counts and evidence-linked moments. Product knowledge supports scenario-scoped draft approval and actual provider checks. Saved background processing can be retried; transcript corrections invalidate derived approvals.

See [the walkthrough](outputs/Prototype_Walkthrough.md) for the demonstration path and remaining user tasks.

## Checks and repeatable preflights

```sh
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m ruff check backend/app backend/tests tools
.venv/bin/python tools/evaluate.py
.venv/bin/python tools/preflight_reasoning.py
.venv/bin/python tools/evaluate_local.py
pnpm --dir frontend build
```

Tests explicitly isolate the deterministic provider and an ephemeral database; they do not invoke configured models. `tools/evaluate.py` measures authored rule cases. `tools/evaluate_local.py` invokes the local model and takes longer. Results are written under `outputs/`; authored cases are not independent accuracy validation.

## Actual attribution and known limits

- Local Qwen runs structured extraction, customer/source checks, semantic audit and optional translation. Coverage candidates and downstream rule/template nodes are explicitly labelled.
- Actual Prisma REST output came from a valid 25-second excerpt of reviewed synthetic Timbre speech. An actual 43.12-second Hindi Timbre WAV decoded correctly. This is a synthetic integration check, not a real customer study.
- A valid 24.4-second Shivani/Avinash two-voice Batch job is saved for resume and was queued at the latest check. Batch diarization and timestamp quality are not claimed.
- The 4B auditor produced false positives on faithful paraphrases and conditions distributed across fields. All model findings need review; confidence is uncalibrated. Human listening, independent translation checks and blind evaluation remain necessary before quality claims.
- Localhost only, demo roles rather than authentication, one API process, SQLite snapshots and local jobs. No production multitenancy, distributed worker, migration or cloud-hosting claim. Runtime audio/database and verification metadata are in ignored `work/`.

See [the one-page solution pitch](outputs/Solution_Pitch.md), IMPLEMENTATION_STATUS.md and docs/SCOPE_MATRIX.md for the project summary and feature coverage.
