import pytest
from fastapi.testclient import TestClient

from backend.app import semantic
from backend.app.knowledge import documents
from backend.app.main import app
from backend.app.reasoning import (
    ExtractionResult,
    add_catalogue_coverage_candidates,
    apply_extraction,
)
from backend.app.reviews import review
from backend.app.schemas import ReviewRequest
from backend.app.workflow import audit

from .test_workflow import canonical, complete_reviews, conversation

client = TestClient(app)


def test_semantic_audit_rejects_fake_evidence_and_stales_after_edit(monkeypatch):
    c = canonical()
    source = next(s for s in c.segments if s.role == "customer")
    target = c.requirements[0]
    valid = {
        "finding_type": "altered",
        "severity": "medium",
        "source_segment_id": source.id,
        "source_quote": source.text,
        "target_id": "requirement:" + target.id,
        "downstream_quote": target.description,
        "explanation": "Review this paraphrase.",
        "correction": "Confirm scope with customer.",
    }
    invalid = valid | {"source_quote": "invented quote"}
    monkeypatch.setattr(
        semantic, "structured_completion", lambda *args: {"findings": [valid, invalid]}
    )
    semantic.run(c)
    audit(c)
    assert c.semantic_audit["rejected_candidates"] == 1
    finding = next(f for f in c.findings if f.origin == "model")
    review(
        c,
        ReviewRequest(
            version=c.version,
            action="finding",
            item_id=finding.id,
            changes={"reviewer_status": "dismissed"},
            reason="Faithful paraphrase verified.",
        ),
        "Technical Reviewer",
    )
    assert (
        next(f for f in c.findings if f.id == finding.id).reviewer_status == "dismissed"
    )
    c.requirements[0].description += " New scope."
    audit(c)
    assert c.semantic_audit is None
    assert not any(f.origin == "model" for f in c.findings)


def test_catalogue_coverage_keeps_model_omission_inferred():
    c = conversation(
        [("customer", "Monthly volume is 2000 devices and may reach 10000 next year.")]
    )
    add_catalogue_coverage_candidates(c, documents())
    candidate = next(r for r in c.requirements if r.capability_id == "scale")
    assert candidate.extraction_origin == "catalogue_coverage"
    assert candidate.information_status == "inferred"
    assert candidate.evidence[0].quote == c.segments[0].text
    with pytest.raises(ValueError, match="Confirm inferred"):
        review(
            c,
            ReviewRequest(
                version=1,
                action="pm",
                item_id=candidate.id,
                changes={"pm_status": "accepted"},
                reason="Test",
            ),
            "Product Manager",
        )


def test_custom_need_remains_unknown_and_discards_invented_constraints():
    c = conversation([("customer", "We need an export of weekly repair totals.")])
    result = ExtractionResult.model_validate(
        {
            "items": [
                {
                    "kind": "need",
                    "segment_id": "s0",
                    "quote": c.segments[0].text,
                    "description": "Export weekly repair totals",
                    "capability_id": None,
                    "information_status": "explicit",
                    "confidence": 0.7,
                    "title": "Weekly export",
                    "constraints": ["weekly", "instant and unlimited"],
                    "acceptance_criteria": [
                        "Confirm export format and reporting period."
                    ],
                }
            ]
        }
    )
    apply_extraction(c, result, documents())
    assert c.requirements[0].capability_id is None
    assert c.requirements[0].constraints == ["weekly"]
    assert c.requirements[0].title == "Weekly export"


def test_discovery_and_pitch_controls():
    denied = client.post(
        "/api/sales/discovery",
        json={
            "title": "Brief",
            "context": "We need QR history.",
            "synthetic_consent": False,
        },
    )
    assert denied.status_code == 422
    c = client.post(
        "/api/sales/discovery",
        json={
            "title": "Brief",
            "context": "We need QR history and private owner details.",
            "synthetic_consent": True,
        },
    ).json()
    assert "discovery brief" in c["source"]
    result = client.post(
        "/api/conversations/" + c["id"] + "/pitch",
        json={"language": "Hindi", "familiarity": "technical"},
    )
    assert result.status_code == 200
    assert result.json()["sources"]
    assert "Technical validation checklist" in result.json()["pitch"]


def test_training_history_reopens_persisted_session():
    session = client.post(
        "/api/training/sessions", json={"scenario_id": "price"}
    ).json()
    client.post(
        "/api/training/sessions/" + session["id"] + "/turns",
        json={"text": "What is your budget?"},
    )
    history = client.get("/api/training/sessions").json()
    assert next(s for s in history if s["id"] == session["id"])["turns"] == 1
    assert (
        client.get("/api/training/sessions/" + session["id"]).json()["turns"][0][
            "trainee"
        ]
        == "What is your budget?"
    )


def test_model_translation_is_unapproved_and_preserves_sources(monkeypatch):
    from backend.app import reasoning

    c = canonical()
    complete_reviews(c)
    monkeypatch.setattr(
        reasoning,
        "structured_completion",
        lambda *args: {
            "text": "ERP compatibility aur API validation chahiye. Personal details hidden rahengi; access test zaroori hai."
        },
    )
    review(
        c,
        ReviewRequest(
            version=1,
            action="draft",
            changes={
                "language": "Hinglish",
                "model_translation": True,
                "detail": "detailed",
            },
        ),
        "Sales Representative",
    )
    assert not c.response.approved
    assert c.response.sources
    assert "Personal details" in c.response.text


def test_knowledge_draft_cannot_influence_answers_until_reviewed():
    body = {
        "title": "Synthetic weekly export",
        "excerpt": "Weekly repairtotals export is supported for a selected reporting period.",
        "keywords": ["repairtotals"],
        "capability_id": "weekly-export",
        "status_value": "supported",
        "criteria": ["A selected week exports repair totals."],
        "synthetic_consent": True,
    }
    draft = client.post("/api/knowledge/documents", json=body)
    assert draft.status_code == 200
    assert (
        client.post("/api/sales/ask", json={"question": "repairtotals"}).json()[
            "status"
        ]
        == "unknown"
    )
    source_id = draft.json()["id"]
    denied = client.post(
        "/api/knowledge/documents/" + source_id + "/approve",
        json={"reason": "Reviewed synthetic feature specification."},
    )
    assert denied.status_code == 409
    approved = client.post(
        "/api/knowledge/documents/" + source_id + "/approve",
        json={"reason": "Reviewed synthetic feature specification."},
        headers={"X-Demo-Role": "Technical Reviewer"},
    )
    assert approved.status_code == 200
    answer = client.post("/api/sales/ask", json={"question": "repairtotals"}).json()
    assert answer["status"] == "supported" and source_id in answer["sources"]
    assert not any(
        d["id"] == source_id for d in client.get("/api/knowledge/drafts").json()
    )


def test_model_enabled_approval_requires_current_semantic_audit(monkeypatch):
    from backend.app.config import settings

    c = canonical()
    complete_reviews(c)
    review(
        c,
        ReviewRequest(version=1, action="draft", changes={"language": "English"}),
        "Sales Representative",
    )
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    with pytest.raises(ValueError, match="semantic audit"):
        review(
            c,
            ReviewRequest(version=1, action="response", changes={"approved": True}),
            "Sales Representative",
        )
    monkeypatch.setattr(
        semantic, "structured_completion", lambda *args: {"findings": []}
    )
    semantic.run(c)
    review(
        c,
        ReviewRequest(version=1, action="response", changes={"approved": True}),
        "Sales Representative",
    )
    assert c.response.approved
    review(
        c,
        ReviewRequest(
            version=1,
            action="response",
            changes={
                "text": c.response.text + " Please confirm next steps.",
                "approved": False,
            },
        ),
        "Sales Representative",
    )
    assert not c.response.approved and c.semantic_audit is None


def test_real_acoustic_measurement_is_observation_not_emotion(tmp_path):
    import math
    import shutil
    import struct
    import wave

    from backend.app.acoustics import measure

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg not installed")
    path = tmp_path / "known-synthetic.wav"
    rate = 16000
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(
            b"".join(
                struct.pack(
                    "<h",
                    int(8000 * math.sin(2 * math.pi * 440 * n / rate))
                    if n < rate
                    else 0,
                )
                for n in range(rate * 2)
            )
        )
    result = measure(path)
    assert result["duration_seconds"] == 2
    assert len(result["silence_spans"]) == 1
    assert 990 <= result["silence_spans"][0]["start_ms"] <= 1010
    assert "does not establish" in result["caveat"]


def test_scripted_experiment_has_controlled_context_and_disclosed_sample():
    result = client.get("/api/insights/experiment").json()
    assert result["synthetic"] is True
    assert len(result["runs"]) == 6
    assert all(
        sum(run["strategy_id"] == strategy["id"] for run in result["runs"]) == 3
        for strategy in result["strategies"]
    )
    assert "authored" in result["caveat"]


def test_shared_topic_does_not_establish_requested_export_support(monkeypatch):
    from backend.app import technical

    c = canonical()
    req = next(r for r in c.requirements if r.capability_id == "repair")
    req.description = "Export weekly repair records as a spreadsheet."
    req.extraction_origin = "model"
    doc = next(d for d in documents() if d["id"] == "kb-repair")
    monkeypatch.setattr(
        technical,
        "structured_completion",
        lambda *args: {
            "checks": [
                {
                    "requirement_id": req.id,
                    "verdict": "not_entailed",
                    "customer_verdict": "entailed",
                    "source_id": "kb-repair",
                    "source_quote": doc["excerpt"],
                    "explanation": "The excerpt documents storage, not exports.",
                }
            ]
        },
    )
    technical.ground(c)
    assessment = next(a for a in c.assessments if a.requirement_id == req.id)
    assert assessment.status == "unknown"
    req.pm_status = "accepted"
    with pytest.raises(ValueError, match="cannot upgrade"):
        review(
            c,
            ReviewRequest(
                version=1,
                action="engineering",
                item_id=req.id,
                changes={"status": "supported"},
                reason="Unsupported upgrade attempt",
            ),
            "Technical Reviewer",
        )


def test_empty_decodable_wav_is_rejected_before_provider_job(monkeypatch, tmp_path):
    import wave

    from backend.app.config import settings

    monkeypatch.setattr(settings, "gnani_api_key_id", "test-key")
    path = tmp_path / "empty.wav"
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
    result = client.post(
        "/api/conversations/upload",
        data={"synthetic_consent": "true"},
        files={"file": ("empty.wav", path.read_bytes(), "audio/wav")},
    )
    assert result.status_code == 422


def test_audit_targets_exclude_evidence_and_original_copies():
    c = canonical()
    target = semantic.targets(c)["requirement:" + c.requirements[0].id]
    assert "original_description" not in target
    assert "original_acceptance_criteria" not in target
    assert "segment_id" not in target


def test_explicit_negation_of_privacy_cannot_pass_word_presence_check():
    from backend.app.workflow import caveat_present

    assert not caveat_present(
        "Owner personal details are not hidden; permission tests are planned.",
        "privacy",
    )
    assert not caveat_present(
        "ERP compatibility is not required and no API is needed.", "erp"
    )
    assert caveat_present(
        "ERP integration depends on API compatibility and sandbox tests.", "erp"
    )


def test_dismissed_model_sentiment_is_not_resurrected_by_keyword_rule():
    from backend.app.schemas import Evidence, Observation
    from backend.app.workflow import signals

    c = conversation([("customer", "I am concerned about privacy?")])
    c.observations = [
        Observation(
            id="obs-model-sentiment",
            kind="sentiment",
            description="Customer explicitly expressed concern.",
            evidence=[
                Evidence(
                    segment_id="s0", quote=c.segments[0].text, speaker_role="customer"
                )
            ],
        )
    ]
    signals(c)
    assert len(c.signals) == 1
    review(
        c,
        ReviewRequest(
            version=1,
            action="observation",
            item_id="obs-model-sentiment",
            changes={"dismissed": True},
            reason="Reviewer corrected an overbroad sentiment label.",
        ),
        "Sales Representative",
    )
    assert c.signals == []


def test_short_clip_limit_is_checked_before_remote_processing(monkeypatch):
    import json
    from types import SimpleNamespace

    from backend.app.config import settings
    from backend.app.routes import conversations

    monkeypatch.setattr(settings, "gnani_api_key_id", "test-key")
    monkeypatch.setattr(
        conversations.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {"streams": [{"codec_type": "audio"}], "format": {"duration": "31"}}
            ).encode(),
        ),
    )
    result = client.post(
        "/api/conversations/upload",
        data={"synthetic_consent": "true", "transcription_mode": "rest"},
        files={"file": ("too-long.wav", b"synthetic-test", "audio/wav")},
    )
    assert result.status_code == 422
    assert "30 seconds" in result.json()["detail"]


def test_pm_change_preserves_before_after_snapshot():
    c = canonical()
    req = c.requirements[0]
    original = req.description
    review(
        c,
        ReviewRequest(
            version=1,
            action="pm",
            item_id=req.id,
            changes={"description": original + " Reviewed clarification."},
            reason="Clarified fictional scope while retaining evidence.",
        ),
        "Product Manager",
    )
    snapshot = next(
        log for log in c.audit_log if log["action"] == "pm_revision_snapshot"
    )
    assert snapshot["before"]["description"] == original
    assert snapshot["after"]["description"].endswith("Reviewed clarification.")
    assert snapshot["before"]["evidence"] == snapshot["after"]["evidence"]
