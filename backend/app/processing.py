"""Persisted, restartable analysis jobs for the single-process local prototype."""

import asyncio
import logging

from . import store
from .reviews import log
from .workflow import analyse

logger = logging.getLogger("voicebridge.processing")
tasks: set[asyncio.Task] = set()


async def run(cid: str):
    try:
        original = store.get(cid)
        updated = await asyncio.to_thread(analyse, original)
        with store.edit(cid, original.version) as current:
            for field in [
                "requirements",
                "observations",
                "assessments",
                "findings",
                "sales",
                "signals",
                "response",
                "node_runs",
            ]:
                setattr(current, field, getattr(updated, field))
            current.status = "ready"
            current.processing_step = None
            current.error = None
            log(
                current,
                "analysis_completed",
                "AI workflow",
                "Derived results are ready for human review.",
            )
    except Exception as exc:  # noqa: BLE001 — persisted job boundary must record failure
        logger.warning(
            "analysis_failed conversation_id=%s error_type=%s", cid, type(exc).__name__
        )
        with store.edit(cid) as current:
            current.status = "failed"
            current.processing_step = None
            current.error = (
                str(exc)
                if isinstance(exc, (ValueError, OSError))
                else "Analysis could not finish. Retry or review the server log."
            )


def launch(cid: str):
    task = asyncio.create_task(run(cid))
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def queue(cid: str):
    with store.edit(cid) as current:
        if current.status not in {"ready", "failed"}:
            raise store.Conflict(
                "This conversation is already processing. Wait for it to finish."
            )
        log(
            current,
            "pre_reanalysis_snapshot",
            "AI workflow",
            "Preserved derived work before regeneration.",
        )
        current.audit_log[-1]["before"] = {
            "requirements": [r.model_dump() for r in current.requirements],
            "assessments": [a.model_dump() for a in current.assessments],
            "sales": current.sales,
        }
        current.response = None
        current.semantic_audit = None
        current.status = "analysing"
        current.error = None
        current.processing_step = "semantic_requirement_extraction"
    launch(cid)
    return store.get(cid)
