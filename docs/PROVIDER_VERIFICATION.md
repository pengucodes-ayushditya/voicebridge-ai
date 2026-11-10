# Actual provider verification — 9 November 2026

## Official contracts

- [Prisma short REST](https://docs.gnani.ai/api/STT/speech-to-text): multipart `audio_file`, explicit `model=prisma-v3.0`, `language_code`, `format`; up to 30 seconds. No returned diarization or timestamps are assumed.
- [Prisma Batch](https://docs.gnani.ai/api/STTBatch/Introduction): create, separate start, bounded status polling, completed-file listing and signed transcript download. The model supports diarization, but actual returned speaker/timestamp quality still needs verification.
- [Timbre REST](https://docs.gnani.ai/api/TTS/tts-inference): `X-API-Key-ID`, model/voice/language and audio_config. Actual calls used timbre-v3.0 with Shivani; synthetic two-voice fixture creation also used Avinash.
- [Official SDK rate-limit notes](https://github.com/Gnani-AI-Mintlify/Gnani-Vachana/blob/main/CHANGELOG.md): Batch reads/start can encounter 429; existing jobs are resumed rather than blindly recreated.
- [Ollama Qwen3 4B](https://ollama.com/library/qwen3:4b): selected local development model. No Evon usage is claimed.

## Returned outputs

1. Actual local Qwen structured extraction and source-grounding preflight: five canonical capability areas preserved, four from model extraction and capacity as an inferred catalogue candidate. All retained evidence quotes validated. See outputs/local-reasoning-preflight.json.
2. Actual Prisma v3.0 REST transcription: Hindi/codemixed text returned from 25 seconds of reviewed synthetic Timbre output. Also exercised through the browser upload and correction flow. See outputs/stt-rest-preflight.json.
3. Actual Timbre v3.0 Hindi WAV: first reviewed response decoded at 43.12 seconds. The gated application endpoint was separately exercised through approval → generation → private audio GET, with HTTP 200 and valid WAV bytes. See outputs/tts-provider-preflight.json and outputs/full-response-loop-preflight.json.
4. Actual local semantic audit and translation candidates: outputs/semantic-audit-preflight.json and outputs/translation-preflight.json. The translation remains unapproved. False positives were observed in the 4B auditor and explicitly dispositioned after engineer review of the fictional source; this does not establish audit accuracy.
5. Valid Prisma Batch test: 24.4 seconds of actual synthetic Shivani/Avinash dialogue. Create/start succeeded; the latest poll remained QUEUED. Audio/job ID are stored privately and the app resumes polling on restart. outputs/speech-provider-preflight.json is the authoritative current result.

The first macOS speech fixture was empty despite a successful command exit; it was cancelled and excluded from successful-call claims. Upload validation now rejects non-empty-container/empty-audio inputs before sending a job.

## Interpretation

These are integration checks on synthetic material, not independent WER, diarization, translation, coaching or business-impact measurements. No output is attributed to Evon or hosted OpenAI. Keys stay in the ignored server-side `.env`; status metadata stores configuration/account fingerprints and timestamps rather than credentials. Successful-call history is not proof of continued credits, account access or service availability. Independent bilingual listening and broader blind evaluation remain needed.
