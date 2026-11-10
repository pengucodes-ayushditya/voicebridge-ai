import asyncio
import json
import subprocess
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    Header,
    HTTPException,
    Response,
    UploadFile,
)
from pydantic import BaseModel, Field

from .. import store
from ..config import ROOT, settings
from ..copilot import Question as CopilotQuestion
from ..jobs import transcribe
from ..providers import GnaniProvider
from ..reviews import ReviewError, gate, log, review
from ..sales_tools import Pitch
from ..schemas import (
    Conversation,
    CreateTranscript,
    Domain,
    ReviewRequest,
    Segment,
    TranscriptEdit,
)
from ..workflow import analyse

router = APIRouter(prefix="/api/conversations")
tasks: set[asyncio.Task] = set()


def launch(cid):
    task = asyncio.create_task(transcribe(cid))
    tasks.add(task)
    task.add_done_callback(tasks.discard)


def new_conversation(
    title, segments, source, domain_id="synthetic-device-lifecycle", background=False
):
    if len({s.id for s in segments}) != len(segments):
        raise HTTPException(422, "Segment IDs must be unique")
    for s in segments:
        s.original_text = s.text
    c = Conversation(
        id=str(uuid4()),
        title=title,
        segments=segments,
        original_segments=[s.model_copy(deep=True) for s in segments],
        source=source,
        domain_id=domain_id,
    )
    if not background:
        c = analyse(c)
    store.save(c)
    return c


@router.get("")
def listing():
    return [
        {
            "id": c.id,
            "title": c.title,
            "status": c.status,
            "source": c.source,
            "domain_id": c.domain_id,
            "requirements": len(c.requirements),
            "open_findings": sum(f.reviewer_status == "open" for f in c.findings),
        }
        for c in store.all_conversations()
    ]


@router.post("/demo", response_model=Conversation)
def demo(
    background_tasks: BackgroundTasks,
    scenario: Domain = "synthetic-device-lifecycle",
    background: bool = False,
):
    raw = json.loads(
        (
            ROOT
            / "data"
            / (
                "marketplace-canonical.json"
                if scenario == "marketplace"
                else "canonical.json"
            )
        ).read_text()
    )
    c = new_conversation(
        raw["title"],
        [Segment.model_validate(s) for s in raw["segments"]],
        "Synthetic fixture · no speech model invoked",
        domain_id=scenario,
        background=background,
    )
    if background:
        from .. import processing

        c.status = "analysing"
        c.processing_step = "semantic_requirement_extraction"
        store.save(c)
        background_tasks.add_task(processing.run, c.id)
    return c


@router.post("", response_model=Conversation)
def create(
    body: CreateTranscript, background_tasks: BackgroundTasks, background: bool = False
):
    c = new_conversation(
        body.title,
        body.segments,
        "User-entered synthetic transcript · no speech model invoked",
        domain_id=body.domain_id,
        background=background,
    )
    if background:
        from .. import processing

        c.status = "analysing"
        c.processing_step = "semantic_requirement_extraction"
        store.save(c)
        background_tasks.add_task(processing.run, c.id)
    return c


@router.post("/upload", response_model=Conversation)
async def upload(
    file: Annotated[UploadFile, File()],
    synthetic_consent: Annotated[bool, Form()] = False,
    transcription_mode: Annotated[str, Form()] = "batch",
    domain_id: Annotated[Domain, Form()] = "synthetic-device-lifecycle",
    title: Annotated[str, Form(max_length=120)] = "",
):
    if not synthetic_consent:
        raise HTTPException(422, "Confirm that this is consented synthetic audio.")
    GnaniProvider().require_key()
    if transcription_mode not in ["batch", "rest"]:
        raise HTTPException(422, "Choose Batch or short-clip REST transcription.")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in [
        ".wav",
        ".mp3",
        ".m4a",
        ".ogg",
        ".flac",
        ".webm",
        ".aac",
        ".amr",
        ".opus",
        ".mp4",
    ]:
        raise HTTPException(422, "Unsupported audio extension.")
    data = await file.read(10 * 1024 * 1024 + 1)
    if not data or len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Upload a non-empty file no larger than 10 MiB.")
    cid = str(uuid4())
    path = ROOT / "work" / f"{cid}{ext}"
    path.write_bytes(data)
    try:
        probe = await asyncio.to_thread(
            subprocess.run,
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type:format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            timeout=15,
        )
        info = json.loads(probe.stdout)
        if (
            probe.returncode
            or not info.get("streams")
            or float(info.get("format", {}).get("duration", 0)) <= 0
        ):
            raise ValueError("No non-empty decodable audio stream")
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(
            422, "The file is not decodable audio. FFmpeg/ffprobe must be installed."
        ) from exc
    if transcription_mode == "rest":
        duration = json.loads(probe.stdout).get("format", {}).get("duration")
        if duration is None or float(duration) > 30:
            path.unlink(missing_ok=True)
            raise HTTPException(
                422,
                "Short-clip REST accepts up to 30 seconds. Use Batch for longer or multiple-speaker recordings.",
            )
    c = Conversation(
        id=cid,
        title=title.strip()
        or "Synthetic audio · " + (Path(file.filename or "recording").stem)[:80],
        source="Gnani Batch audio upload"
        if transcription_mode == "batch"
        else "Gnani REST short audio upload · no diarization",
        transcription_mode=transcription_mode,
        audio_path=str(path),
        domain_id=domain_id,
        status="queued",
        transcription_model="Pending real Gnani call",
    )
    store.save(c)
    launch(cid)
    return c


@router.get("/{cid}", response_model=Conversation)
def detail(cid: str):
    return store.get(cid)


@router.patch("/{cid}/transcript", response_model=Conversation)
def update_transcript(
    cid: str,
    body: TranscriptEdit,
    background_tasks: BackgroundTasks,
    x_demo_role: str = Header(default="Sales Representative"),
    background: bool = False,
):
    with store.edit(cid, body.version) as c:
        if len({s.id for s in body.segments}) != len(body.segments):
            raise HTTPException(422, "Segment IDs must be unique")
        if c.status not in ["ready", "failed"]:
            raise store.Conflict(
                "Wait for processing to finish before editing the transcript."
            )
        original = {s.id: s.original_text or s.text for s in c.original_segments}
        if {s.id for s in c.segments} != {s.id for s in body.segments}:
            raise HTTPException(422, "This editor preserves original segment IDs.")
        c.segments = [
            s.model_copy(update={"original_text": original[s.id]})
            for s in body.segments
        ]
        if background:
            c.status = "analysing"
            c.processing_step = "semantic_requirement_extraction"
            c.response = None
            c.semantic_audit = None
            c.error = None
        else:
            updated = analyse(c)
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
                setattr(c, field, getattr(updated, field))
        log(c, "transcript_correction", x_demo_role, body.reason)
    if background:
        from .. import processing

        background_tasks.add_task(processing.run, cid)
    return store.get(cid)


@router.post("/{cid}/review", response_model=Conversation)
def review_action(
    cid: str,
    body: ReviewRequest,
    background_tasks: BackgroundTasks,
    x_demo_role: str = Header(default="Sales Representative"),
    background: bool = False,
):
    if body.action == "analyse" and background:
        with store.edit(cid, body.version) as current:
            if current.status not in ["ready", "failed"]:
                raise store.Conflict("Analysis is already in progress.")
            log(
                current,
                "pre_reanalysis_snapshot",
                x_demo_role,
                "Preserved prior work before regeneration.",
            )
            current.audit_log[-1]["before"] = {
                "requirements": [r.model_dump() for r in current.requirements],
                "assessments": [a.model_dump() for a in current.assessments],
            }
            current.response = None
            current.semantic_audit = None
            current.status = "analysing"
            current.processing_step = "semantic_requirement_extraction"
            current.error = None
        from .. import processing

        background_tasks.add_task(processing.run, cid)
        return store.get(cid)
    with store.edit(cid, body.version) as c:
        if c.status not in ["ready", "failed"]:
            raise store.Conflict(
                "Wait for processing to finish before reviewing this conversation."
            )
        if body.action == "analyse":
            log(
                c,
                "pre_reanalysis_snapshot",
                x_demo_role,
                "Preserved previous derived work before regenerating analysis.",
            )
            c.audit_log[-1]["before"] = {
                field: getattr(c, field)
                if field == "sales"
                else [item.model_dump() for item in getattr(c, field)]
                for field in [
                    "requirements",
                    "assessments",
                    "findings",
                    "observations",
                    "sales",
                ]
            }
            updated = analyse(c)
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
                setattr(c, field, getattr(updated, field))
            log(c, "reanalysis", x_demo_role, "All downstream approvals invalidated")
        else:
            review(c, body, x_demo_role)
    return store.get(cid)


@router.post("/{cid}/transcribe", response_model=Conversation)
async def resume(cid: str):
    GnaniProvider().require_key()
    c = store.get(cid)
    if not c.audio_path:
        raise HTTPException(422, "No uploaded audio for this conversation.")
    if c.status not in ["failed", "ready"]:
        raise HTTPException(409, "A transcription job is already active.")
    with store.edit(cid) as c:
        log(
            c,
            "transcription_retry",
            "Sales Representative",
            "Resumed saved job; cleared downstream approvals before replacing the transcript.",
        )
        c.audit_log[-1]["before"] = {
            "segments": [s.model_dump() for s in c.segments],
            "requirements": [r.model_dump() for r in c.requirements],
            "response": c.response.model_dump() if c.response else None,
        }
        c.requirements = []
        c.assessments = []
        c.observations = []
        c.findings = []
        c.signals = []
        c.sales = {}
        c.response = None
        c.semantic_audit = None
        c.node_runs = []
        c.status = "queued"
        c.error = None
    launch(cid)
    return store.get(cid)


@router.post("/{cid}/audio", response_model=Conversation)
async def speak(cid: str, x_demo_role: str = Header(default="Sales Representative")):
    if x_demo_role != "Sales Representative":
        raise ReviewError("Switch to Sales Representative for customer speech.")
    c = store.get(cid)
    gate(c)
    if not c.response or not c.response.approved:
        raise ReviewError(
            "Approve the exact customer response before generating audio."
        )
    audio = await GnaniProvider().speak(c.response.text, c.response.language)
    path = ROOT / "work" / f"{cid}-response.wav"
    with store.edit(cid, c.version) as current:
        path.write_bytes(audio)
        current.response.audio_path = str(path)
        log(
            current,
            "timbre_audio",
            x_demo_role,
            settings.gnani_tts_model + " · " + settings.gnani_tts_voice,
        )
    return store.get(cid)


@router.get("/{cid}/audio")
def audio(cid: str):
    c = store.get(cid)
    if not c.response or not c.response.audio_path:
        raise HTTPException(404, "No reviewed audio generated.")
    return Response(
        Path(c.response.audio_path).read_bytes(),
        media_type="audio/wav",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/{cid}/handoff")
def handoff(cid: str, format: str = "json"):
    c = store.get(cid)
    if format == "markdown":
        lines = [
            "# " + c.title,
            "",
            "VoiceBridge AI · " + c.domain_id,
            "",
            "## Customer context",
            "",
        ]
        lines.extend(
            "> " + s.text.replace("\n", "\n> ")
            for s in c.segments
            if s.role == "customer"
        )
        lines.extend(["", "## Reviewed requirements", ""])
        for requirement in c.requirements:
            if requirement.superseded_by:
                continue
            assessment = next(
                (a for a in c.assessments if a.requirement_id == requirement.id), None
            )
            lines.extend(
                [
                    "### " + requirement.title,
                    "",
                    requirement.description,
                    "",
                    f"Priority: {requirement.priority} · Intent: {requirement.information_status} · PM: {requirement.pm_status}",
                    "",
                    requirement.user_story,
                    "",
                    "Acceptance checks:",
                ]
            )
            lines.extend("- " + item for item in requirement.acceptance_criteria)
            lines.extend(["", "Customer evidence:"])
            lines.extend(
                f'- [{ev.segment_id}] "{ev.quote}"' for ev in requirement.evidence
            )
            if assessment:
                lines.extend(
                    [
                        "",
                        f"Technical status: {assessment.status} · Review: {assessment.reviewer_status}",
                        "",
                        assessment.explanation,
                        "",
                        "Dependencies:",
                    ]
                )
                lines.extend("- " + item for item in assessment.dependencies)
                lines.extend(["", "Open questions:"])
                lines.extend("- " + item for item in assessment.clarification_questions)
                lines.extend(
                    ["", "Sources: " + ", ".join(assessment.documentation_sources)]
                )
                if assessment.notes:
                    lines.extend(["", "Reviewer note: " + assessment.notes])
            lines.append("")
        lines.extend(["## Integrity findings", ""])
        lines.extend(
            f"- {f.severity} · {f.finding_type} · {f.reviewer_status}: {f.description}"
            for f in c.findings
        )
        if c.response:
            lines.extend(
                [
                    "",
                    "## Customer response",
                    "",
                    "Approved: " + str(c.response.approved),
                    "",
                    c.response.text,
                ]
            )
        return Response(
            "\n".join(lines),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="voicebridge-{cid}.md"'
            },
        )
    if format != "json":
        raise HTTPException(422, "Choose json or markdown export.")
    return Response(
        c.model_dump_json(indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="voicebridge-{cid}.json"'
        },
    )


@router.delete("/{cid}")
def remove(cid: str):
    c = store.get(cid)
    if c.status not in ["ready", "failed"]:
        raise HTTPException(409, "Wait for the active job before deleting.")
    for path in [c.audio_path, c.response.audio_path if c.response else None]:
        if path:
            Path(path).unlink(missing_ok=True)
    store.delete(cid)
    return {"deleted": True}


@router.post("/{cid}/pitch")
def pitch_variant(cid: str, body: Pitch):
    from ..sales_tools import make_pitch

    return make_pitch(store.get(cid), body)


@router.post("/{cid}/acoustics")
def audio_observations(cid: str):
    from ..acoustics import measure

    c = store.get(cid)
    if not c.audio_path:
        raise HTTPException(422, "Upload audio before measuring acoustic observations.")
    try:
        result = measure(Path(c.audio_path))
        if c.segments and result["duration_seconds"] > 0:
            result["transcript_tokens_per_minute"] = round(
                sum(len(segment.text.split()) for segment in c.segments)
                / result["duration_seconds"]
                * 60,
                1,
            )
            result["pace_caveat"] = (
                "Whitespace-token estimate across the recording, including pauses and all speakers; tokenisation differs by language. Not a fluency, confidence or emotion score."
            )
        return result
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise HTTPException(
            422, "Audio measurement failed. Check FFmpeg and the uploaded audio."
        ) from exc


class TurnPart(BaseModel):
    role: str
    text: str = Field(min_length=1, max_length=10000)


class SplitTranscript(BaseModel):
    version: int
    segment_id: str
    parts: list[TurnPart] = Field(min_length=2, max_length=30)
    reason: str = Field(min_length=5, max_length=1000)


@router.post("/{cid}/split-transcript", response_model=Conversation)
def split_transcript(
    cid: str, body: SplitTranscript, background_tasks: BackgroundTasks
):
    """Split exact source text into reviewed roles without inventing timings."""
    with store.edit(cid, body.version) as c:
        if c.status not in {"ready", "failed"}:
            raise store.Conflict("Wait for processing before splitting the transcript.")
        parent = next((s for s in c.segments if s.id == body.segment_id), None)
        if parent is None:
            raise HTTPException(422, "Transcript segment not found.")
        cursor = 0
        children = []
        for part in body.parts:
            if part.role not in {"customer", "sales", "unknown"}:
                raise HTTPException(
                    422, "Choose Customer, Sales or Unassigned for every turn."
                )
            chunk = part.text.strip()
            position = parent.text.find(chunk, cursor)
            if not chunk or position < 0 or parent.text[cursor:position].strip():
                raise HTTPException(
                    422,
                    "Each turn must preserve the original wording in order. Only whitespace may be omitted between turns.",
                )
            cursor = position + len(chunk)
            children.append(
                Segment(
                    id=parent.id + "-" + uuid4().hex[:6],
                    speaker_id=part.role,
                    role=part.role,
                    text=chunk,
                    original_text=chunk,
                    language=parent.language,
                    parent_segment_id=parent.id,
                )
            )
        if parent.text[cursor:].strip() or len(c.segments) - 1 + len(children) > 300:
            raise HTTPException(422, "Keep every spoken word and at most 300 turns.")
        c.segments = [
            child
            for s in c.segments
            for child in (children if s.id == parent.id else [s])
        ]
        c.original_segments.extend(s.model_copy(deep=True) for s in children)
        c.transcript_lineage.append(
            {
                "parent": parent.model_dump(),
                "child_ids": [s.id for s in children],
                "reason": body.reason,
            }
        )
        c.response = None
        c.semantic_audit = None
        c.status = "analysing"
        c.processing_step = "semantic_requirement_extraction"
        log(c, "transcript_split", "Sales Representative", body.reason)
    from .. import processing

    background_tasks.add_task(processing.run, cid)
    return store.get(cid)


class SessionTurn(BaseModel):
    version: int
    text: str = Field(min_length=1, max_length=10000)
    role: str = "customer"
    synthetic_consent: bool


@router.post("/{cid}/turns", response_model=Conversation)
def append_turn(cid: str, body: SessionTurn, background_tasks: BackgroundTasks):
    if not body.synthetic_consent or body.role not in {"customer", "sales"}:
        raise HTTPException(
            422, "Confirm fictional content and choose Customer or Sales."
        )
    with store.edit(cid, body.version) as c:
        if c.status not in {"ready", "failed"}:
            raise store.Conflict(
                "Wait for the current analysis before adding another turn."
            )
        if len(c.segments) >= 300:
            raise HTTPException(
                422, "This conversation has reached the 300-turn limit."
            )
        segment = Segment(
            id="turn-" + uuid4().hex[:8],
            speaker_id=body.role,
            role=body.role,
            text=body.text,
            original_text=body.text,
        )
        c.segments.append(segment)
        c.original_segments.append(segment.model_copy(deep=True))
        c.response = None
        c.semantic_audit = None
        c.status = "analysing"
        c.processing_step = "semantic_requirement_extraction"
        log(
            c,
            "conversation_turn_added",
            "Sales Representative",
            "Added a fictional session note; downstream approvals will be regenerated.",
        )
    from .. import processing

    background_tasks.add_task(processing.run, cid)
    return store.get(cid)


@router.post("/{cid}/copilot")
def contextual_copilot(cid: str, body: CopilotQuestion):
    from ..copilot import assist

    c = store.get(cid)
    if body.version is not None and c.version != body.version:
        raise store.Conflict(
            "This conversation changed. Reload before asking with the updated context."
        )
    if c.status not in {"ready", "failed"}:
        raise store.Conflict("Wait for the current conversation analysis.")
    suggestion = assist(body, c)
    with store.edit(cid, c.version) as current:
        current.copilot_history.append(suggestion | {"context_version": c.version})
        log(current, "sales_assistance", "Sales Representative", suggestion["provider"])
    return {"suggestion": suggestion, "conversation": store.get(cid)}


@router.get("/{cid}/recording")
def recording(cid: str):
    from fastapi.responses import FileResponse

    c = store.get(cid)
    if not c.audio_path or not Path(c.audio_path).exists():
        raise HTTPException(404, "No source recording attached.")
    return FileResponse(c.audio_path, headers={"Cache-Control": "no-store"})


@router.get("/{cid}/workflow")
def workflow_status(cid: str):
    from ..journey import describe

    return describe(store.get(cid))
