# Guided prototype update — 10 November 2026

The prototype now follows Conversation → Sales Copilot → Requirements → Engineering → Customer response. It uses the latest unbranded marketplace scenario alongside the original device-lifecycle example. Each screen exposes its local demo-role actions directly; optional controls are collapsed and evidence/history remain accessible.

Added contextual AI sales assistance with exact source citations, optional AI pitch tailoring, plain-language customer drafts, AI Academy coaching with actual trainee quotes, background analysis/progress/recovery, transcript splitting with lineage, session turns, original recording replay, workflow readiness/blockers and Markdown handoffs. Product knowledge is scoped by scenario. Server-side review gates and stale-audit invalidation remain enforced. Original wording and snapshots are preserved.

Actual Ollama/qwen3:4b extraction, source checking, sales Q&A, response drafting, semantic audit and Academy coaching were exercised. The approved response generated real Gnani Timbre audio; its 20-second excerpt returned real Prisma REST text. REST has no diarization/timestamps. Batch verification remains pending.

The small local auditor produces false positives: candidates require human review. Audio energy and pauses are observations, not emotion diagnoses. Local demo roles are not production authentication. SQLite, one API process and local files remain the runtime design.

See outputs/Prototype_Walkthrough.md for the demonstration path and user tasks; outputs/Prototype_Live_Validation.json records actual calls. Earlier reports below remain historical evidence.

# VoiceBridge AI — prototype status, 9 November 2026

The local prototype implements the connected customer → sales → PM → engineering → customer workflow. Submission work is deferred at the user's request. This document distinguishes implemented behaviour from quality validation and external service completion.

## Implemented prototype milestones

- Next.js/React/TypeScript frontend and FastAPI/Pydantic/LangGraph/SQLAlchemy SQLite backend, configurable synthetic catalogue, preserved original transcripts, optimistic versions and review history.
- Native Ollama structured extraction with `qwen3:4b`; optional OpenAI adapter. Versioned extraction prompt, exact customer-quote checks, structured custom needs/criteria/questions, explicit versus inferred labels and unknown technical scope.
- Clearly labelled inferred catalogue coverage candidates surface known-topic omissions without silently marking them customer-confirmed. A capacity omission in the canonical fixture is preserved this way.
- Separate checks compare proposed needs with customer evidence and the complete request with source documents. Unsupported extensions such as exporting records when only storage is documented remain unknown and cannot be upgraded through a shared topic alone.
- Synthetic transcript import and discovery brief; validated audio upload with progress; Batch job persistence/recovery; explicit ≤30-second REST mode; global speaker-role mapping, per-turn edits and original evidence preservation.
- Grounded Sales Copilot, sourced answers, fit gaps, escalation, next question and editable/copyable pitch variants for English/Hindi/Hinglish and business/technical audiences.
- PM editing, priorities, confirmation status, theme groups, overlap hints, merge/split lineage and engineering handoff export. Engineering rationale, dependencies, notes and conservative approval bounds.
- Rule auditing plus on-demand local semantic candidates with exact source and target validation. Material edits invalidate stale model comparisons. Final model-enabled response approval requires an audit of the exact saved response and disposition of high-severity candidates.
- Short/detailed customer explanations, reviewed catalogue translations and optional model translation of custom technical wording. Translation remains an unapproved draft requiring bilingual review; exact-text approval and speech gates remain separate.
- Three persisted three-turn Academy scenarios, history/reopen, source-grounded product Q&A, transparent rubric, actual trainee quotes and question-specific alternatives.
- Actual stored-conversation aggregates, evidence-linked expressed-wording candidates and dismissal, six-run clearly authored pitch-comparison fixture, on-demand measured audio energy/silence and estimated transcript token pace. No emotion or causal sales claim is inferred.
- Source-draft creation, explicit Technical Reviewer approval and retrieval isolation. Drafts cannot influence answers; approved custom capabilities can extend the synthetic catalogue. Initial source versions are immutable rather than a production document-management system.

## Real provider verification

- **Ollama qwen3:4b:** actual structured extraction, source checks, semantic audit and a single-summary baseline have run locally.
- **Prisma v3.0 REST:** actual Hindi transcription returned from a valid 25-second excerpt of reviewed Timbre speech. The same upload/transcription/correction path was verified in the browser. REST provides neither timestamps nor diarization; none are invented.
- **Timbre v3.0:** actual Shivani Hindi WAV returned, 43.12 seconds, decoded successfully. A valid fictional two-voice fixture was also synthesized with Shivani and Avinash.
- **Prisma Batch:** the valid 24.4-second two-voice job was accepted and started but remained queued at the last check. Its ID/audio are saved; the application can resume polling. Batch result quality, speaker separation and returned timestamps remain unverified.
- The initial macOS-generated fixture was discovered to contain no audio, cancelled and excluded from successful-call claims. Empty uploads are now rejected before creating jobs.
- No Evon or hosted OpenAI output is claimed.

## Verification and evidence

- Backend tests and lint pass; final counts are recorded in outputs/PROTOTYPE_MILESTONE_REPORT.md.
- Production frontend build/type checking pass. Browser verification used an isolated database/API instance and exercised discovery, conservative unknown scope, source approval, complete Academy, real REST upload, progress, role mapping and acoustic measurements.
- Fifteen authored local-model capability cases matched their coarse labels with valid retained quotes. This run predates the later source-entailment addition; it does not validate that stage or establish general multilingual accuracy. Repeat with tools/evaluate_local.py.
- The 4B semantic auditor produced false positives in an actual canonical check. They were individually inspected and dispositioned in the synthetic review preflight. Treat all model findings as review candidates; independent precision/recall and bilingual assessment remain outstanding.

## Remaining verification and operating limits

Prisma Batch completion/diarization is externally pending. Independent multilingual listening, translation review and broader blind evaluation are still needed before quality claims. Energy/pauses are measured; pitch variation and emotion are not. The app is localhost-only with demo roles, a single API process, local jobs and SQLite snapshots; production auth, tenant isolation, durable workers, migrations and cloud deployment are future hardening rather than claimed capabilities.
