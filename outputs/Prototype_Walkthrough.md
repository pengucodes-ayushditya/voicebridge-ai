# VoiceBridge AI — updated prototype walkthrough

Open **http://localhost:3000**. Keep Ollama running. No further setup or credentials are needed with the existing local `.env`.

## Follow the customer’s intent

1. **Workspace → Marketplace cold-start** creates the unbranded video scenario. The device-lifecycle example remains available separately. These are synthetic text fixtures; they call the configured reasoning model, not speech recognition.
2. **Conversation** shows the original words, speaker roles and source-linked needs. Upload/record audio to call Gnani Prisma. Quick clips (≤30 seconds) return no speaker separation: use **Split into turns** and assign Customer/Sales before analysis. Longer recordings use the resumable Batch job. Review original audio and wording before correcting anything.
3. **Sales Copilot** answers the customer’s question using approved product sources and conversation context. Open source chips. Check conditions, suggested follow-up and actual provider. Tailor an editable pitch in English, Hindi or Hinglish, review it, then mark it reviewed.
4. **Requirements** presents one need at a time with evidence, proposed acceptance checks and clarification questions. Confirm inferred scope with the customer before accepting it. Record a decision rationale. Themes and merge/split tools are under **Organize scope**.
5. **Engineering** keeps scope separate from feasibility. Review source support, dependencies, unknowns, risks and questions. Edit the technical assessment with a reason, within its approved-source support bound. Approve each accepted requirement’s assessment.
6. **Customer response** shows remaining blockers. Generate a plain-language AI draft or explicitly choose the source-based version. Save edits, check intent on the exact saved text, review high-priority candidates and approve the response. Only then generate actual Gnani Timbre audio. Export Markdown or JSON handoffs.

The workspace handles each local demo role in the appropriate screen; there is no role-switching puzzle. These demo roles are not production authentication. Review history and source evidence remain available throughout.

## The rest of the workspace

- **Sales Academy:** three personas per product scenario, three-turn practice, persisted history, transparent baseline rubric and optional AI coaching grounded in the trainee’s actual words.
- **Insights:** saved-conversation counts, language coverage and evidence-linked communication moments. Audio observations measure recording energy and low-energy spans; they do not diagnose emotions or prove satisfaction. The authored pitch experiment is labelled separately.
- **Product knowledge:** approved, scenario-scoped sources; draft and Technical Reviewer approval; actual configured provider names and a connection check. Draft documents are excluded from retrieval.
- **Delete conversation:** available within the conversation header after explicit confirmation; export first if needed.

## What you need to do

1. Try the marketplace example from start to finish and review the wording with your teammate.
2. Bring the consented fictional customer/sales recording. Use Batch for the whole conversation, or a ≤30-second clip for the verified short-clip path. Listen and assign roles yourself where necessary.
3. Supply your real approved product documents when moving beyond the synthetic examples. Product support and prices cannot be inferred from a demo conversation.
4. Independently review Hindi/Hinglish wording and generated speech before presenting it.

## Restart

From the project root:

```sh
.venv/bin/python tools/run_local.py
```

Open Ollama from Applications first. Stop the existing launcher with Ctrl-C before starting another. For development, append `--dev`. Credentials stay in the root `.env` and are never sent to the browser.

## Practical limits

The installed development model is `ollama/qwen3:4b`. Evon is selectable later when an actual compatible installed model is available; provider labels describe actual calls. The 4B model can over-extract scope and produce false-positive intent findings. Source/target quotes are validated, but this is not independent proof of semantic correctness. Human review remains essential.

Prisma REST and Timbre were exercised with actual outputs during this update. Batch diarization remains dependent on the saved Gnani job/account service; no new Batch success or timestamp-quality claim is made. This is a local, single-process prototype without live telephony, production authentication or a distributed worker.
