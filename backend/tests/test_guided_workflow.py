"""Guided workflow contracts: scope, source lineage and real-model validation."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.app import copilot, processing, store
from backend.app.claims import unsupported_claims
from backend.app.config import settings
from backend.app.journey import describe
from backend.app.knowledge import documents, retrieve
from backend.app.main import app
from backend.app.reasoning import ReasoningError
from backend.app.schemas import Conversation, Segment

client = TestClient(app)


def test_knowledge_is_scoped_to_selected_product():
    market = documents("marketplace")
    lifecycle = documents("synthetic-device-lifecycle")
    assert market and lifecycle
    assert not {d["id"] for d in market} & {d["id"] for d in lifecycle}
    assert retrieve("cold-start recommendation", "marketplace")
    assert not retrieve("cold-start recommendation", "synthetic-device-lifecycle")


def test_marketplace_background_analysis_and_reviewed_handoff():
    created = client.post(
        "/api/conversations/demo?scenario=marketplace&background=true"
    )
    assert created.status_code == 200
    c = client.get("/api/conversations/" + created.json()["id"]).json()
    assert c["status"] == "ready" and c["domain_id"] == "marketplace"
    assert len(c["requirements"]) == 3
    base = "/api/conversations/" + c["id"]
    assert not client.get(base + "/workflow").json()["can_draft"]
    for requirement in c["requirements"]:
        assert requirement["evidence"]
        r = client.post(
            base + "/review",
            headers={"X-Demo-Role": "Product Manager"},
            json={
                "version": c["version"],
                "action": "pm",
                "item_id": requirement["id"],
                "changes": {"pm_status": "accepted", "information_status": "explicit"},
                "reason": "Confirmed customer scope against source evidence.",
            },
        )
        assert r.status_code == 200, r.text
        c = r.json()
        r = client.post(
            base + "/review",
            headers={"X-Demo-Role": "Technical Reviewer"},
            json={
                "version": c["version"],
                "action": "engineering",
                "item_id": requirement["id"],
                "changes": {"reviewer_status": "approved"},
                "reason": "Reviewed source prerequisites and pilot evaluation dependencies.",
            },
        )
        assert r.status_code == 200, r.text
        c = r.json()
    assert client.get(base + "/workflow").json()["can_draft"]
    r = client.post(
        base + "/review",
        headers={"X-Demo-Role": "Sales Representative"},
        json={
            "version": c["version"],
            "action": "draft",
            "changes": {"language": "English", "detail": "short"},
        },
    )
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["response"] and not c["response"]["approved"]
    assert "market" in " ".join(c["response"]["sources"])
    export = client.get(base + "/handoff?format=markdown")
    assert (
        export.status_code == 200 and "text/markdown" in export.headers["content-type"]
    )
    assert c["requirements"][0]["title"] in export.text


def test_split_preserves_source_and_rejects_word_loss():
    c = Conversation(
        id="split-guided",
        title="Source preservation",
        source="manual",
        status="ready",
        segments=[
            Segment(
                id="original",
                speaker_id="unknown",
                text="Can you help? Let us review the data.",
                original_text="Can you help? Let us review the data.",
            )
        ],
    )
    c.original_segments = [s.model_copy(deep=True) for s in c.segments]
    store.save(c)
    base = "/api/conversations/" + c.id
    payload = {
        "version": c.version,
        "segment_id": "original",
        "parts": [
            {"role": "customer", "text": "Can you help?"},
            {"role": "sales", "text": "review the data."},
        ],
        "reason": "Reviewed speaker boundaries.",
    }
    assert client.post(base + "/split-transcript", json=payload).status_code == 422
    payload["parts"][1]["text"] = "Let us review the data."
    result = client.post(base + "/split-transcript", json=payload)
    assert result.status_code == 200, result.text
    updated = client.get(base).json()
    assert [s["role"] for s in updated["segments"]] == ["customer", "sales"]
    assert all(
        s["start_ms"] is None and s["parent_segment_id"] == "original"
        for s in updated["segments"]
    )
    assert updated["original_segments"][0]["text"] == c.segments[0].text
    assert updated["transcript_lineage"][0]["parent"]["text"] == c.segments[0].text


def test_failed_job_is_persisted_and_cannot_draft(monkeypatch):
    c = Conversation(
        id="job-failure-guided", title="Failure", source="manual", status="analysing"
    )
    store.save(c)

    def fail(_):
        raise RuntimeError("internal test failure")

    monkeypatch.setattr(processing, "analyse", fail)
    asyncio.run(processing.run(c.id))
    updated = store.get(c.id)
    assert updated.status == "failed" and "Retry" in updated.error
    assert not describe(updated)["can_draft"]
    assert describe(updated)["blockers"][0]["code"] == "failed"


def test_model_citations_are_validated_before_use(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    doc = retrieve("cold-start", "marketplace")[0]
    result = {
        "status": "conditional",
        "answer": "The approach depends on catalogue data and pilot review.",
        "next_question": "What data is available?",
        "objection_response": "That is a reasonable concern.",
        "escalation_required": True,
        "escalation_reason": "Validate the inputs.",
        "citations": [{"source_id": doc["id"], "quote": doc["excerpt"]}],
    }
    monkeypatch.setattr(copilot, "structured_completion", lambda *a: result)
    answer = copilot.assist(
        copilot.Question(question="cold-start", domain_id="marketplace")
    )
    assert answer["model_used"] and answer["sources"] == [doc["id"]]
    result["citations"][0]["quote"] = "Invented source words"
    with pytest.raises(ReasoningError, match="invalid product citation"):
        copilot.assist(copilot.Question(question="cold-start", domain_id="marketplace"))


def test_claim_guard_recognises_explicit_denial():
    assert not unsupported_claims("Recommendation quality isn't guaranteed.")
    assert unsupported_claims("Recommendation quality is guaranteed.") == [
        "guaranteed",
        "guarantee",
    ]


def test_coaching_rejects_invented_trainee_quote(monkeypatch):
    from backend.app import coaching

    monkeypatch.setattr(
        coaching,
        "structured_completion",
        lambda *a: {
            "summary": "Review the source.",
            "strengths": [],
            "next_practice": [],
            "examples": [
                {
                    "turn": 1,
                    "quote": "Invented trainee words",
                    "feedback": "Review",
                    "alternative": "Review catalogue data and pilot criteria.",
                    "source_ids": ["kb-market-cold-start"],
                }
            ],
        },
    )
    with pytest.raises(ReasoningError, match="actual wording"):
        coaching.coach(
            {
                "complete": True,
                "domain_id": "marketplace",
                "scenario": {},
                "turns": [
                    {
                        "customer": "How?",
                        "trainee": "We should review the product data.",
                    }
                ],
            }
        )


def test_transcription_retry_clears_old_approvals(monkeypatch):
    from backend.app.providers import GnaniProvider
    from backend.app.routes import conversations
    from backend.app.schemas import CustomerResponse

    monkeypatch.setattr(GnaniProvider, "require_key", lambda self: None)
    monkeypatch.setattr(conversations, "launch", lambda cid: None)
    c = Conversation(
        id="retry-review-guided",
        title="Retry",
        source="audio",
        status="failed",
        audio_path="synthetic-test.wav",
        response=CustomerResponse(
            text="Old approved text", language="English", approved=True, sources=[]
        ),
    )
    store.save(c)
    r = client.post("/api/conversations/" + c.id + "/transcribe")
    assert r.status_code == 200
    assert r.json()["status"] == "queued" and r.json()["response"] is None
    assert r.json()["audit_log"][-1]["before"]["response"]["approved"]
