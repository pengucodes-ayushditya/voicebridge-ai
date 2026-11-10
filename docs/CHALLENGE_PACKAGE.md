> Historical submission draft from the earlier milestone. Submission work is deferred. Its attribution statements are superseded by IMPLEMENTATION_STATUS.md and PROVIDER_VERIFICATION.md; do not publish it unchanged.

# Challenge preparation package — draft, unpublished

## Written explanation

VoiceBridge AI addresses an enterprise communication problem: customers describe operational needs in ordinary and regional language, while sales, product and engineering each need a different view of that conversation. During these handoffs, conditions can disappear and an optimistic statement can become an unsupported commitment.

VoiceBridge provides a connected workspace for customer evidence, product fit, grounded product answers, requirements, PM decisions, technical assessment, integrity review and a customer-friendly return response. Its differentiator is the Intent Integrity Auditor: original wording remains inspectable beside downstream records, and the workflow requires humans to address high-severity findings before producing a final response.

The synthetic ReNew Devices scenario asks for device QR history, central repair/diagnostic records, restricted partner access without owner personal information, ERP integration and increasing volume. A sales turn promises “any ERP” and complete partner history. The prototype flags both claims, retains the privacy constraint, classifies ERP and partner access as conditional, and leaves capacity unknown pending workload definition and testing.

The frontend uses Next.js, React, TypeScript and Tailwind. FastAPI, Pydantic and a narrow LangGraph pipeline implement analysis and review logic. SQLAlchemy/SQLite persists versioned conversation snapshots and scripted training sessions. A controlled approved JSON knowledge base grounds capability mappings and product answers. Provider adapters implement the documented Gnani Prisma Batch and Timbre WAV APIs behind the backend. They are tested with mocked HTTP responses; no credentials have been available for a successful live call.

**Current attribution must remain exact:** no live Gnani, Evon or external reasoning-model calls were used in this milestone. A configurable OpenAI Responses adapter now supports strict structured semantic extraction and exact evidence checks, but has only been tested with mocked HTTP. Synthetic transcripts, deterministic fallback extraction, audit rules, scripted coaching and localised templates are explicitly labelled. Do not claim any model-powered outputs until a successful live preflight is captured.

Fifteen curated synthetic cases cover English, Hindi, Hinglish, unknown questions, privacy, objections, integration prerequisites, changed/conflicting statements, capacity and offline limits. The executable evaluation checks capability presence, four-state feasibility, evidence validity and seeded universal-ERP promises. Results are recorded in evaluation-results.json. These tests were authored with the implementation and are not independent validation of language understanding or business outcomes. Real speech quality, acoustic measurements, translation review and a single-LLM baseline remain unmeasured.

The Academy demonstrates three scripted three-turn buyer scenarios and an eight-category heuristic coaching scorecard quoting the actual trainee response. Insights counts actual stored synthetic conversations and provides evidence-linked language observations, while showing insufficient-data guidance for small samples. It makes no emotion-truth, employee-ranking or causal-performance claim.

The remaining work is documented in SCOPE_MATRIX.md: live model verification, model-backed drift auditing, richer review operations, and challenge publication. There is no production authentication, multitenancy or cloud deployment. Team, repository, host and video links must be supplied and verified before submission.

## 110-second recording script

This script is ready to record against the actual app. **No video has been recorded.** If credentials remain unavailable, label the demonstration “deterministic synthetic workflow preview,” show the missing-key provider panel, and omit claims of real transcription/synthesis. For a challenge-complete video, first complete the real-provider preflight.

| Time | Actual screen/action | Narration |
|---|---|---|
| 0–10 s | Overview and connected loop | “Customer intent can change each time sales, product and engineering retell the conversation. VoiceBridge keeps the evidence connected.” |
| 10–25 s | Upload consented synthetic Hinglish audio; show actual Prisma output when available. Otherwise load visibly labelled fixture. | “Here a refurbishment business asks for QR history, service records and private partner access.” |
| 25–40 s | Sales Copilot fit, kb-erp source and unknown certification question | “Recommendations use approved knowledge. ERP compatibility is conditional; undocumented claims remain unknown.” |
| 40–50 s | Academy, one actual turn and completed scorecard from a prior recorded session | “The same knowledge supports trainee practice, with coaching tied to their own wording.” |
| 50–70 s | Requirements evidence, accepted PM record and approved technical assessment | “Every requirement retains the customer's quote. People review priorities, acceptance checks and technical conditions.” |
| 70–85 s | Integrity findings, original privacy quote and suggested correction | “The auditor catches ‘any ERP’ and the access promise that conflicts with owner privacy.” |
| 85–105 s | Reviewed Hinglish customer response; play actual Timbre WAV only after successful real call | “The answer returns to the customer with the conditions intact. Voice output uses only the exact reviewed text.” |
| 105–110 s | Overview / title and confirmed team credit | “VoiceBridge AI: intent, intact. Synthetic demonstration for the Gnani.ai Great Indian Internship Challenge.” |

Prepare PM/engineering reviews in advance for pacing, but record actual state changes and disclose fixtures. Do not simulate live provider loading or add fake API badges. Use captions and keep keys, private account pages and unrelated applications out of frame.

## LinkedIn draft — requires final links, names and model validation

Customer requirements shouldn’t lose their meaning between sales, product and engineering.

We’re building VoiceBridge AI for the Gnani.ai Great Indian Internship Challenge: a connected workspace for multilingual customer conversations, grounded sales guidance, trainee practice, evidence-linked requirements, technical review and clear customer explanations.

Our Intent Integrity Auditor highlights where an overpromise or missing privacy condition changes the customer's intent. The demo uses a synthetic refurbished-device scenario; no real customer calls are included.

Current prototype status: working local deterministic workflow, with documented Gnani Prisma/Timbre adapters awaiting live account verification. We will update model attribution after actual successful calls.

Before publishing, insert verified demo/repository links and agreed teammate names/contributions. If real models are used later, replace the status paragraph with their actual model versions and observed role. No claim of sales uplift or production readiness.

## X draft — adapt after verification

We’re building VoiceBridge AI: customer evidence → grounded sales guidance → reviewed engineering handoffs → clear customer responses. Its Intent Integrity Auditor catches lost constraints and overpromises. Synthetic local workflow demo; real-model validation pending. Add verified demo + team credit before publishing.

## Submission checklist

- [ ] Verify portal URL, deadline, video limit, eligibility and exact posting requirements against the actual participant portal.
- [ ] Securely configure and verify real Prisma/Timbre model access; record truthful attribution.
- [ ] Resolve remaining P0 items in SCOPE_MATRIX.md; rerun tests/evaluation.
- [ ] Human-review synthetic Hindi/Hinglish transcription, translations and generated audio.
- [ ] Confirm team names, roles and exact contributions. No names invented.
- [ ] Record actual application video with readable captions and audible narration.
- [ ] Select a full-stack host, configure authentication/access and verify the repeatable demo from a clean browser.
- [ ] Confirm source repository and demo/video URLs. No repository was created remotely in this milestone.
- [ ] Review written/social drafts against the implementation and actual model calls.
- [ ] Publish/post only under explicit publication instructions and verify returned links.
- [ ] Submit against the verified portal checklist. Nothing has been submitted.
