from fastapi import APIRouter, BackgroundTasks, Header

from .. import training
from ..config import settings
from ..copilot import Question, assist
from ..knowledge import documents
from ..knowledge_admin import NewSource, SourceApproval
from ..sales_tools import Discovery
from ..schemas import Domain
from ..store import all_conversations

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "service": "VoiceBridge AI", "synthetic_only": True}


@router.get("/providers/status")
def providers():
    configured = bool(settings.gnani_api_key_id)
    from ..verification import reasoning_success, success

    reasoning_at = reasoning_success()
    batch_at = success("stt", settings.gnani_stt_model)
    rest_at = success("stt-rest", settings.gnani_stt_model)
    stt_at = batch_at or rest_at
    tts_at = success("tts", settings.gnani_tts_model, settings.gnani_tts_voice)
    reasoning_configured = bool(settings.llm_model) and (
        settings.llm_provider == "ollama"
        or (settings.llm_provider == "openai" and bool(settings.llm_api_key))
    )
    return {
        "stt": {
            "provider": "Gnani",
            "model": settings.gnani_stt_model,
            "configured": configured,
            "verified": bool(stt_at),
            "verified_at": stt_at,
            "verification_mode": "batch" if batch_at else "rest" if rest_at else None,
            "status": (
                "Batch call recorded · quality review required"
                if batch_at
                else "REST call recorded · Batch diarization unverified"
            )
            if stt_at
            else "Configured · account/model access unverified"
            if configured
            else "Blocked · GNANI_API_KEY_ID missing",
        },
        "tts": {
            "provider": "Gnani",
            "model": settings.gnani_tts_model,
            "voice": settings.gnani_tts_voice,
            "configured": configured,
            "verified": bool(tts_at),
            "verified_at": tts_at,
            "status": "Successful call recorded · quality review still required"
            if tts_at
            else "Configured · account/model access unverified"
            if configured
            else "Blocked · GNANI_API_KEY_ID missing",
        },
        "reasoning": {
            "provider": settings.llm_provider
            if settings.llm_provider in {"openai", "ollama"}
            else "deterministic-demo",
            "model": settings.llm_model or None,
            "configured": reasoning_configured,
            "verified": bool(reasoning_at),
            "verified_at": reasoning_at,
            "status": (
                "Successful structured extraction recorded · quality review required"
                if reasoning_at
                else "Configured · model access unverified"
                if reasoning_configured
                else "Blocked · configure LLM_MODEL and the selected provider"
                if settings.llm_provider in {"openai", "ollama"}
                else "Deterministic demo rules · no reasoning model called"
            ),
        },
        "evon": {"status": "Hosted access not configured or verified"},
    }


@router.get("/knowledge/documents")
def knowledge(domain_id: Domain | None = None):
    return documents(domain_id)


@router.post("/sales/ask")
def ask(body: Question):
    return assist(body)


@router.get("/training/scenarios")
def scenarios():
    return training.SCENARIOS


@router.post("/training/sessions")
def start(body: training.StartSession):
    return training.start(body.scenario_id)


@router.get("/training/sessions/{sid}")
def session(sid: str):
    return training.get(sid)


@router.post("/training/sessions/{sid}/turns")
def turn(sid: str, body: training.Turn):
    return training.turn(sid, body.text)


@router.get("/insights")
def insights(domain_id: Domain | None = None):
    cs = [
        c for c in all_conversations() if domain_id is None or c.domain_id == domain_id
    ]
    return {
        "sample_size": len(cs),
        "ready_count": sum(c.status == "ready" for c in cs),
        "reviewed_responses": sum(bool(c.response and c.response.approved) for c in cs),
        "observation_counts": {
            kind: sum(
                o.kind == kind and not o.dismissed for c in cs for o in c.observations
            )
            for kind in ["question", "objection", "constraint", "sentiment"]
        },
        "observations": [
            {"conversation_id": c.id, "conversation_title": c.title, **o.model_dump()}
            for c in cs
            for o in c.observations
            if not o.dismissed
        ],
        "synthetic": True,
        "signals": [
            {"conversation_id": c.id, "conversation_title": c.title, **s}
            for c in cs
            for s in c.signals
        ],
        "language_counts": {
            lang: sum(
                any((s.language or "unknown") == lang for s in c.segments) for c in cs
            )
            for lang in {s.language or "unknown" for c in cs for s in c.segments}
        },
        "caveat": "Descriptive counts of synthetic conversations only. Languages can overlap. No causal or employee-performance inference. Acoustic observations are measured separately per uploaded recording, not aggregated here.",
        "data_insufficient": len(cs) < 10,
    }


@router.post("/sales/discovery")
def discovery(
    body: Discovery, background_tasks: BackgroundTasks, background: bool = False
):
    from ..schemas import Segment
    from .conversations import new_conversation

    c = new_conversation(
        body.title,
        [
            Segment(
                id="brief-1",
                speaker_id="customer-brief",
                role="customer",
                text=body.context,
            )
        ],
        "Synthetic customer discovery brief · no speech model invoked",
        domain_id=body.domain_id,
        background=background,
    )
    if background:
        from .. import processing, store

        c.status = "analysing"
        c.processing_step = "semantic_requirement_extraction"
        store.save(c)
        background_tasks.add_task(processing.run, c.id)
    return c


@router.get("/training/sessions")
def training_history():
    return training.history()


@router.get("/insights/experiment")
def comparison_experiment():
    import json

    from ..config import ROOT

    return json.loads((ROOT / "data/communication_experiment.json").read_text())


@router.get("/knowledge/drafts")
def knowledge_drafts(domain_id: Domain | None = None):
    from ..knowledge_admin import all_sources

    return [
        d
        for d in all_sources()
        if d["status"] == "draft"
        and (
            domain_id is None
            or d.get("domain_id", "synthetic-device-lifecycle") == domain_id
        )
    ]


@router.post("/knowledge/documents")
def create_source(body: NewSource):
    from ..knowledge_admin import create

    return create(body)


@router.post("/knowledge/documents/{sid}/approve")
def approve_source(
    sid: str,
    body: SourceApproval,
    x_demo_role: str = Header(default="Sales Representative"),
):
    from ..knowledge_admin import approve
    from ..reviews import ReviewError

    if x_demo_role != "Technical Reviewer":
        raise ReviewError("Switch to Technical Reviewer to approve a source.")
    return approve(sid, body.reason)


@router.get("/domains")
def domains():
    from ..knowledge import domain_config

    return [
        {
            "id": key,
            "label": domain_config(key)["label"],
            "persona": domain_config(key)["user_persona"],
        }
        for key in ["synthetic-device-lifecycle", "marketplace"]
    ]


@router.post("/providers/check")
async def check_providers():
    import httpx

    result = providers()
    if settings.llm_provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    settings.ollama_base_url.rstrip("/") + "/api/tags"
                )
                response.raise_for_status()
                names = [m.get("name") for m in response.json().get("models", [])]
                reachable = settings.llm_model in names
                result["reasoning"]["reachable"] = reachable
                result["reasoning"]["status"] = (
                    "Local model is installed and server is reachable"
                    if reachable
                    else "Ollama is reachable; the configured model is not installed"
                )
        except (httpx.HTTPError, ValueError, TypeError):
            result["reasoning"]["reachable"] = False
            result["reasoning"]["status"] = (
                "Ollama is offline. Start Ollama, then check again."
            )
    return result


@router.post("/training/sessions/{sid}/coach")
def training_coach(sid: str):
    from ..coaching import coach
    from ..store import lock

    session = training.get(sid)
    result = coach(session)
    with lock:
        current = training.get(sid)
        current["ai_coaching"] = result
        training.save(current)
    return current
