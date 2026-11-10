## Guided workspace update

The React client is split into task-focused workspace components. A server-derived journey contract supplies versioned readiness and blockers. Contextual copilot history and transcript lineage persist with conversations. Background jobs save processing progress. Scenario-scoped approved sources feed extraction, sales, engineering and coaching. Existing endpoints enforce review, evidence, version and approval gates. See IMPLEMENTATION_STATUS.md for actual provider validation and limits.

# VoiceBridge AI — local prototype architecture

## Runtime and boundaries

Next.js/React/TypeScript renders one role-oriented workspace and proxies `/api` to FastAPI. Pydantic validates conversation/review contracts. SQLAlchemy stores versioned JSON conversation snapshots, Academy sessions and source drafts in SQLite. A single API process and local background jobs are intentional prototype limits; demo roles are not authentication.

The LangGraph path is semantic extraction → source/evidence grounding and feasibility → catalogue sales guidance → communication signals → rule integrity audit. Audio ingestion, remote job polling, human review, on-demand semantic audit, customer translation and speech generation have explicit boundaries outside that graph. Node runs record provider, schema/prompt version, duration and completion; narrow nested source checks have their own model provenance.

## Model and knowledge paths

`reasoning.py` supports native local Ollama structured output and optional OpenAI Responses structured output. Local development selects `qwen3:4b`, thinking disabled, bounded requests and schema validation. The current extraction prompt is `prompts/semantic_extraction_v3.md`. Quote acceptance requires an existing customer segment and an exact substring. Model proposals may create custom unknown needs; known-topic coverage candidates are visibly inferred rather than falsely confirmed.

`technical.py` separately checks whether a proposed need follows from its customer evidence and whether its complete requested behaviour follows from an approved source. Invalid/missing checks fail closed to unknown. A shared topic cannot establish extra behaviour. Customer confirmation and source support are distinct bounds. The model remains fallible; reviewers inspect the actual sources.

`knowledge.py` combines eight reviewed synthetic base documents with approved custom sources from `knowledge_admin.py`. New drafts are isolated until Technical Reviewer approval. Custom capability IDs cannot overwrite existing approved capabilities. First versions are immutable; a full production document-revision system is not claimed.

## Integrity and review

Rule checks detect known overpromises, privacy/criteria loss, changed wording, exclusions, assumptions and missing response caveats. `semantic.py` provides an explicit model comparison across original segments, authored sales/requirement/assessment text and the exact response. Evidence/original copies are excluded from downstream comparison targets. Exact source/target references are validated; model candidates show their origin and target. Material content changes invalidate a fingerprinted semantic comparison. Candidate dispositions preserve rationale.

PM and engineering edits retain before/after snapshots, source evidence and reasons. Merge/split preserves lineage and starts new scope as inferred/unknown. Model-enabled final approval requires a current semantic comparison of the exact saved response plus review of high-severity candidates. Finding dispositions unapprove existing response audio without discarding the response draft. Translation candidates remain unapproved; bilingual review is required. Timbre generation requires exact response approval and all PM/engineering gates.

## Speech

`providers.py` implements Prisma Batch create/start/status/files and REST `/stt/v3`, plus Timbre WAV inference. Empty/undecodable uploads are rejected locally. Short REST clips are bounded to 30 seconds and preserve missing diarization/timestamps as unknown/null. Batch jobs persist the remote ID before start, poll at ten-second intervals, and recover on startup or resume. GET/start rate limits retry with bounds; create POST is not blindly retried. Signed transcript downloads use an allowlist and never receive API credentials.

`verification.py` records successful-call timestamps bound to account/model/voice/configuration. This is historical provenance, not a current-service SLA or a quality score. Only actual returned outputs can mark a path verified.

## Other modules

Academy sessions are persisted scripted simulations with transparent rules, actual trainee quotes and contextual alternatives. Product Q&A shares the same approved knowledge. Insights uses actual stored sample/language counts. A separate six-run comparison fixture is explicitly authored, not measured customer behaviour. FFmpeg measures energy and silence spans; estimated whitespace-token pace includes pauses and is not an emotion/fluency score.

## Validation and operation

Unit tests isolate credentials/provider configuration and use ephemeral storage. Real-call and local-model reports are separate from authored rule metrics. Browser checks use a separate database/API instance. `.env` and all runtime artifacts stay out of the source archive. Cloud deployment, production auth/tenancy, durable workers, schema migrations and independent language/voice validation remain future work or verification limits.
