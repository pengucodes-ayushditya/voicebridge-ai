import json

import pytest
from pydantic import ValidationError

from backend.app.config import ROOT
from backend.app.knowledge import answer
from backend.app.reviews import ReviewError, review
from backend.app.schemas import Conversation, Requirement, ReviewRequest, Segment
from backend.app.workflow import analyse, caveat_present

CASES = json.loads((ROOT / "data/evaluation.json").read_text())


def conversation(turns):
    return Conversation(
        id="test",
        title="Test",
        source="Test fixture",
        segments=[
            Segment(id=f"s{i}", speaker_id=role, role=role, text=text)
            for i, (role, text) in enumerate(turns)
        ],
    )


def canonical():
    raw = json.loads((ROOT / "data/canonical.json").read_text())
    return analyse(
        Conversation(
            id="canonical",
            title=raw["title"],
            source="fixture",
            segments=raw["segments"],
        )
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_gold_capabilities_and_feasibility(case):
    c = analyse(conversation(case["turns"]))
    assert {r.capability_id for r in c.requirements if r.capability_id} == set(
        case["capabilities"]
    )
    statuses = {
        r.capability_id: next(
            a.status for a in c.assessments if a.requirement_id == r.id
        )
        for r in c.requirements
    }
    for key, value in case["statuses"].items():
        assert statuses[key] == value
    assert (
        any(f.finding_type == "unsupported_promise" for f in c.findings)
        == case["promise"]
    )
    if case.get("conflict") or case.get("revision"):
        assert any(f.finding_type == "contradictory" for f in c.findings)
    for r in c.requirements:
        for e in r.evidence:
            s = next(s for s in c.segments if s.id == e.segment_id)
            assert e.quote == s.text and s.role == "customer"


def test_assumptions_cannot_masquerade_as_customer_facts():
    with pytest.raises(ValidationError):
        Requirement(
            id="x",
            title="x",
            description="x",
            original_description="x",
            category="x",
            confidence=0.5,
            user_story="x",
            evidence=[],
        )


def test_invalid_timestamps():
    with pytest.raises(ValidationError):
        Segment(id="s", speaker_id="x", text="x", start_ms=500, end_ms=100)


def test_unknown_and_conditional_answers():
    assert answer("ISO 27001 certification?")["status"] == "unknown"
    assert answer("Does any ERP work?")["status"] == "conditional"
    assert answer("Fully offline?")["status"] == "unsupported"


def test_customer_response_is_blocked_without_reviews():
    c = canonical()
    with pytest.raises(ReviewError):
        review(c, ReviewRequest(version=1, action="draft"), "Sales Representative")


def complete_reviews(c):
    for r in list(c.requirements):
        review(
            c,
            ReviewRequest(
                version=1,
                action="pm",
                item_id=r.id,
                changes={"pm_status": "accepted"},
                reason="Verified customer evidence",
            ),
            "Product Manager",
        )
        review(
            c,
            ReviewRequest(
                version=1,
                action="engineering",
                item_id=r.id,
                changes={"reviewer_status": "approved"},
                reason="Source verified, conditions retained",
            ),
            "Technical Reviewer",
        )
    for f in list(c.findings):
        review(
            c,
            ReviewRequest(
                version=1,
                action="finding",
                item_id=f.id,
                changes={"reviewer_status": "resolved"},
                reason="Corrected the proposed promise and will explain limitations.",
            ),
            "Technical Reviewer",
        )


@pytest.mark.parametrize("language", ["English", "Hindi", "Hinglish"])
def test_full_reviewed_flow_and_caveats(language):
    c = canonical()
    complete_reviews(c)
    review(
        c,
        ReviewRequest(version=1, action="draft", changes={"language": language}),
        "Sales Representative",
    )
    assert caveat_present(c.response.text, "erp")
    assert caveat_present(c.response.text, "privacy")
    review(
        c,
        ReviewRequest(version=1, action="response", changes={"approved": True}),
        "Sales Representative",
    )
    assert c.response.approved
    assert not any(f.finding_type == "caveat_loss" for f in c.findings)


def test_response_edit_cannot_remove_caveat():
    c = canonical()
    complete_reviews(c)
    review(c, ReviewRequest(version=1, action="draft"), "Sales Representative")
    with pytest.raises(ReviewError):
        review(
            c,
            ReviewRequest(
                version=1,
                action="response",
                changes={"text": "Everything works.", "approved": True},
            ),
            "Sales Representative",
        )


def test_pm_edit_preserves_evidence_and_invalidates_approval():
    c = canonical()
    complete_reviews(c)
    r = next(r for r in c.requirements if r.capability_id == "privacy")
    original = r.evidence.copy()
    review(
        c,
        ReviewRequest(
            version=1,
            action="pm",
            item_id=r.id,
            changes={"description": "Partners see everything"},
            reason="Seeded unsafe edit for audit",
        ),
        "Product Manager",
    )
    assert next(r for r in c.requirements if r.id == "req-privacy").evidence == original
    assert (
        next(
            a for a in c.assessments if a.requirement_id == "req-privacy"
        ).reviewer_status
        == "pending"
    )
    assert any(
        f.finding_type == "constraint_loss" and f.id == "finding-edit-req-privacy"
        for f in c.findings
    )


def test_wrong_demo_role_is_rejected():
    c = canonical()
    with pytest.raises(ReviewError):
        review(
            c,
            ReviewRequest(
                version=1,
                action="pm",
                item_id=c.requirements[0].id,
                changes={"pm_status": "accepted"},
                reason="test",
            ),
            "Sales Representative",
        )
