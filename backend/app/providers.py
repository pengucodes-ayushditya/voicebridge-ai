"""Gnani HTTP adapters. Contracts verified against docs.gnani.ai on 2026-11-09."""

import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import settings
from .schemas import Segment


class ProviderError(ValueError):
    pass


class MissingCredentials(ProviderError):
    pass


class GnaniProvider:
    def __init__(self, key=None, transport=None):
        self.key = settings.gnani_api_key_id if key is None else key
        self.transport = transport

    def require_key(self):
        if not self.key:
            raise MissingCredentials(
                "Gnani credentials are missing. Set GNANI_API_KEY_ID server-side; sample transcripts are available separately."
            )

    async def request(self, method, path, **kwargs):
        self.require_key()
        async with httpx.AsyncClient(
            base_url=settings.gnani_base_url, timeout=60, transport=self.transport
        ) as client:
            retryable = method == "GET" or path.endswith("/start")
            attempts = 5 if retryable else 1
            for attempt in range(attempts):
                try:
                    r = await client.request(
                        method, path, headers={"X-API-Key-ID": self.key}, **kwargs
                    )
                except httpx.RequestError as exc:
                    # POST create is deliberately not retried, to avoid duplicate jobs.
                    if method == "GET" and attempt < attempts - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise ProviderError(
                        "Gnani network request failed; retry from the application."
                    ) from exc
                if (
                    r.status_code in [429, 502, 503, 504]
                    and retryable
                    and attempt < attempts - 1
                ):
                    try:
                        delay = min(
                            max(
                                float(r.headers.get("Retry-After", str(2**attempt))), 0
                            ),
                            30,
                        )
                    except ValueError:
                        delay = 2**attempt
                    await asyncio.sleep(delay)
                    continue
                if not r.is_success:
                    raise ProviderError(
                        f"Gnani returned HTTP {r.status_code}. Check account access, enabled model and credits."
                    )
                return r
        raise ProviderError("Gnani retry budget exhausted")

    async def create_job(self, path: Path):
        config = {
            "model": settings.gnani_stt_model,
            "language_code": "indic-auto",
            "mode": "transcribe",
            "with_diarization": True,
            "num_speakers": 2,
        }
        if settings.gnani_stt_model == "prisma-v3.0":
            config["format"] = "codemix"
        r = await self.request(
            "POST",
            "/stt/v3/batch/jobs",
            files={
                "config": (None, json.dumps(config), "application/json"),
                "files": (path.name, path.read_bytes(), "application/octet-stream"),
            },
        )
        try:
            return str(r.json()["job_id"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Malformed Gnani create response") from exc

    async def transcribe_short(self, path: Path):
        data = {"model": settings.gnani_stt_model, "language_code": "indic-auto"}
        if settings.gnani_stt_model == "prisma-v3.0":
            data["format"] = "codemix"
        response = await self.request(
            "POST",
            "/stt/v3",
            data=data,
            files={
                "audio_file": (path.name, path.read_bytes(), "application/octet-stream")
            },
        )
        try:
            raw = response.json()
            text = raw["transcript"]
            if (
                raw.get("success") is not True
                or not isinstance(text, str)
                or not text.strip()
                or raw.get("model") != settings.gnani_stt_model
            ):
                raise ValueError("Unexpected short-clip transcript")
            from .verification import record_success

            record_success("stt-rest", settings.gnani_stt_model, self.key)
            return [
                Segment(
                    id="s1",
                    speaker_id="unknown",
                    role="unknown",
                    text=text,
                    original_text=text,
                    language=raw.get("detected_language_code"),
                )
            ]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError(
                "Gnani short-clip response was empty or did not match the requested model."
            ) from exc

    async def start(self, jid):
        await self.request("POST", f"/stt/v3/batch/jobs/{jid}/start")

    async def status(self, jid):
        try:
            return (await self.request("GET", f"/stt/v3/batch/jobs/{jid}")).json()[
                "status"
            ]
        except ProviderError:
            raise
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("Malformed Gnani status response") from exc

    async def result(self, jid):
        try:
            payload = (
                await self.request(
                    "GET",
                    f"/stt/v3/batch/jobs/{jid}/files",
                    params={"status": "COMPLETED"},
                )
            ).json()
            files = payload["data"]
            if not files:
                raise ProviderError(
                    "No completed transcript file was returned. The audio may contain no recognisable speech."
                )
            url = files[0]["transcript_url"]
            parsed = urlparse(url)
            # Do not send API credentials to signed storage URLs or follow arbitrary redirects.
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or not (
                    parsed.hostname.endswith(".amazonaws.com")
                    or parsed.hostname.endswith(".vachana.ai")
                )
            ):
                raise ProviderError(
                    "Unrecognised transcript storage host; adapter review required."
                )
            async with httpx.AsyncClient(
                timeout=60, transport=self.transport
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                raw = r.json()
            segments = self.normalise(raw)
            from .verification import record_success

            record_success("stt", settings.gnani_stt_model, self.key)
            return segments
        except (KeyError, TypeError, ValueError, httpx.HTTPError) as exc:
            if isinstance(exc, ProviderError):
                raise
            raise ProviderError(
                "Gnani transcript response was malformed or unavailable."
            ) from exc

    @staticmethod
    def normalise(raw):
        segments = []
        for i, s in enumerate(raw.get("segments", [])):
            if not s.get("text", "").strip():
                continue
            segments.append(
                Segment(
                    id=f"s{i + 1}",
                    speaker_id=str(s.get("speaker_id", "unknown")),
                    role="unknown",
                    text=s["text"],
                    original_text=s["text"],
                    start_ms=round(s["start_time"] * 1000)
                    if s.get("start_time") is not None
                    else None,
                    end_ms=round(s["end_time"] * 1000)
                    if s.get("end_time") is not None
                    else None,
                    language=s.get("language_detected") or raw.get("language_code"),
                )
            )
        if not segments and raw.get("full_transcript"):
            segments = [
                Segment(
                    id="s1",
                    speaker_id="unknown",
                    text=raw["full_transcript"],
                    original_text=raw["full_transcript"],
                    language=raw.get("language_code"),
                )
            ]
        if not segments:
            raise ProviderError("Gnani returned an empty transcript.")
        return segments

    async def speak(self, text, language):
        lang = {"English": "en-IN", "Hindi": "hi-IN", "Hinglish": "hi-en"}[language]
        r = await self.request(
            "POST",
            "/api/v1/tts/inference",
            json={
                "text": text,
                "voice": settings.gnani_tts_voice,
                "model": settings.gnani_tts_model,
                "language": lang,
                "speed": 1.0,
                "audio_config": {
                    "sample_rate": 24000,
                    "num_channels": 1,
                    "sample_width": 2,
                    "encoding": "linear_pcm",
                    "container": "wav",
                },
            },
        )
        if not r.content.startswith(b"RIFF"):
            raise ProviderError("Gnani did not return the requested WAV audio.")
        from .verification import record_success

        record_success(
            "tts", settings.gnani_tts_model, self.key, settings.gnani_tts_voice
        )
        return r.content
