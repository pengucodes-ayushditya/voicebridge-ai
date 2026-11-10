import asyncio
import logging
from pathlib import Path

from . import store
from .config import settings
from .providers import GnaniProvider, ProviderError

logger = logging.getLogger("voicebridge.jobs")


async def transcribe(cid):
    provider = GnaniProvider()
    try:
        c = store.get(cid)
        if c.transcription_mode == "rest":
            segments = await provider.transcribe_short(Path(c.audio_path))
            with store.edit(cid) as current:
                current.segments = segments
                current.original_segments = [s.model_copy(deep=True) for s in segments]
                current.status = "ready"
                current.error = None
                current.transcription_model = (
                    settings.gnani_stt_model + " · REST, no diarization/timestamps"
                )
            return
        if not c.provider_job_id:
            jid = await provider.create_job(Path(c.audio_path))
            with store.edit(cid) as c:
                c.provider_job_id = jid
                c.status = "created"
        else:
            jid = c.provider_job_id
        status = await provider.status(jid)
        if status == "CREATED":
            await provider.start(jid)
        for _ in range(90):
            status = await provider.status(jid)
            with store.edit(cid) as c:
                c.status = status.lower()
            if status in ["COMPLETED", "PARTIAL_FAILURE"]:
                segments = await provider.result(jid)
                with store.edit(cid) as c:
                    c.segments = segments
                    c.original_segments = [s.model_copy(deep=True) for s in segments]
                    c.status = "ready"
                    c.error = None
                    c.transcription_model = settings.gnani_stt_model
                return
            if status in ["FAILED", "START_FAILED", "CANCELLED", "EXPIRED"]:
                raise ProviderError(
                    "Gnani job ended with "
                    + status
                    + ". Review audio, model access and account credits."
                )
            await asyncio.sleep(10)
        raise ProviderError(
            "Transcription timed out after 15 minutes. The job ID was saved; retry to resume polling."
        )
    except (ProviderError, OSError, ValueError) as exc:
        logger.warning(
            "transcription_failed conversation_id=%s error_type=%s",
            cid,
            type(exc).__name__,
        )
        with store.edit(cid) as c:
            c.status = "failed"
            c.error = str(exc)
