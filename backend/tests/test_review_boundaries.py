import pytest

from backend.app.reviews import ReviewError, review
from backend.app.schemas import ReviewRequest

from .test_workflow import canonical, complete_reviews


def test_technical_edit_cannot_turn_conditional_into_guarantee():
    c = canonical()
    complete_reviews(c)
    with pytest.raises(ReviewError, match="upgrade"):
        review(
            c,
            ReviewRequest(
                version=1,
                action="engineering",
                item_id="req-erp",
                changes={"status": "supported"},
                reason="Try to remove condition",
            ),
            "Technical Reviewer",
        )


def test_technical_dependency_loss_rejected():
    c = canonical()
    complete_reviews(c)
    with pytest.raises(ReviewError, match="dependency"):
        review(
            c,
            ReviewRequest(
                version=1,
                action="engineering",
                item_id="req-erp",
                changes={"dependencies": []},
                reason="Remove checks",
            ),
            "Technical Reviewer",
        )


def test_custom_engineering_text_is_versioned_and_not_silently_template_translated():
    c = canonical()
    complete_reviews(c)
    review(
        c,
        ReviewRequest(
            version=1,
            action="engineering",
            item_id="req-erp",
            changes={
                "explanation": "API compatibility remains unconfirmed; the sandbox is unavailable.",
                "status": "unknown",
                "reviewer_status": "approved",
            },
            reason="Sandbox access unavailable",
        ),
        "Technical Reviewer",
    )
    assert c.audit_log[-2]["before"]["status"] == "conditional"
    assert c.audit_log[-2]["after"]["status"] == "unknown"
    with pytest.raises(ReviewError, match="custom reviewer wording"):
        review(
            c,
            ReviewRequest(version=1, action="draft", changes={"language": "Hinglish"}),
            "Sales Representative",
        )
    review(
        c,
        ReviewRequest(version=1, action="draft", changes={"language": "English"}),
        "Sales Representative",
    )
    assert "sandbox is unavailable" in c.response.text


def test_privacy_acceptance_criteria_edits_are_audited():
    c = canonical()
    r = next(r for r in c.requirements if r.id == "req-privacy")
    review(
        c,
        ReviewRequest(
            version=1,
            action="pm",
            item_id=r.id,
            changes={"acceptance_criteria": ["Partner can see records"]},
            reason="Seeded dropped test",
        ),
        "Product Manager",
    )
    assert any(
        f.id == "finding-criteria-req-privacy" and f.severity == "high"
        for f in c.findings
    )


def test_acknowledging_high_severity_issue_does_not_unlock_response():
    c = canonical()
    complete_reviews(c)
    c.findings[0].reviewer_status = "acknowledged"
    with pytest.raises(ReviewError, match="high-severity"):
        review(c, ReviewRequest(version=1, action="draft"), "Sales Representative")


def test_assumed_need_needs_confirmation_before_acceptance():
    c = canonical()
    r = c.requirements[0]
    r.information_status = "assumption"
    with pytest.raises(ReviewError, match="Confirm"):
        review(
            c,
            ReviewRequest(
                version=1,
                action="pm",
                item_id=r.id,
                changes={"pm_status": "accepted"},
                reason="Not yet confirmed",
            ),
            "Product Manager",
        )


def test_valid_negative_claim_language_is_approvable():
    c = canonical()
    complete_reviews(c)
    review(
        c,
        ReviewRequest(version=1, action="draft", changes={"language": "English"}),
        "Sales Representative",
    )
    text = (
        c.response.text
        + "\nWe cannot guarantee compatibility with any ERP. There is no unlimited capacity commitment."
    )
    review(
        c,
        ReviewRequest(
            version=1, action="response", changes={"text": text, "approved": True}
        ),
        "Sales Representative",
    )
    assert c.response.approved


def test_merge_preserves_original_records_and_combines_evidence():
    c = canonical()
    original_ids = ["req-qr", "req-repair"]
    review(
        c,
        ReviewRequest(
            version=1,
            action="merge",
            changes={
                "ids": original_ids,
                "title": "Device service timeline",
                "description": "Show QR-linked repair history to authorised users.",
            },
            reason="Combine related timeline needs for review",
        ),
        "Product Manager",
    )
    child = next(r for r in c.requirements if r.supersedes == original_ids)
    assert len(c.requirements) == 6
    assert child.information_status == "inferred" and child.pm_status == "pending"
    assert {e.segment_id for e in child.evidence} == {"s1", "s3"}
    assert all(
        r.superseded_by == [child.id] for r in c.requirements if r.id in original_ids
    )
    assert (
        next(a for a in c.assessments if a.requirement_id == child.id).status
        == "unknown"
    )
    assert not any(f.finding_type == "omitted" for f in c.findings)


def test_split_preserves_privacy_checks_and_requires_confirmation():
    c = canonical()
    review(
        c,
        ReviewRequest(
            version=1,
            action="split",
            changes={
                "ids": ["req-privacy"],
                "parts": [
                    {
                        "title": "Assigned partner records",
                        "description": "Partners see assigned service records only.",
                    },
                    {
                        "title": "Hide personal information",
                        "description": "Owner personal information remains hidden.",
                    },
                ],
            },
            reason="Separate access and privacy acceptance checks",
        ),
        "Product Manager",
    )
    children = [r for r in c.requirements if r.supersedes == ["req-privacy"]]
    assert len(children) == 2 and all(
        r.evidence and r.constraints and r.original_acceptance_criteria
        for r in children
    )
    with pytest.raises(ReviewError, match="Confirm"):
        review(
            c,
            ReviewRequest(
                version=1,
                action="pm",
                item_id=children[0].id,
                changes={"pm_status": "accepted"},
                reason="Not yet confirmed",
            ),
            "Product Manager",
        )


def test_refinement_rejects_duplicate_ids_and_wrong_roles():
    c = canonical()
    with pytest.raises(ReviewError, match="distinct"):
        review(
            c,
            ReviewRequest(
                version=1,
                action="merge",
                changes={"ids": ["req-qr", "req-qr"]},
                reason="test",
            ),
            "Product Manager",
        )
    with pytest.raises(ReviewError, match="Product Manager"):
        review(
            c,
            ReviewRequest(
                version=1, action="split", changes={"ids": ["req-qr"]}, reason="test"
            ),
            "Sales Representative",
        )


def test_observations_keep_evidence_when_dismissed():
    c = canonical()
    observation = next(o for o in c.observations if o.kind == "constraint")
    quote = observation.evidence[0].quote
    review(
        c,
        ReviewRequest(
            version=1,
            action="observation",
            item_id=observation.id,
            changes={"dismissed": True},
            reason="Reviewer classification correction",
        ),
        "Sales Representative",
    )
    saved = next(o for o in c.observations if o.id == observation.id)
    assert saved.dismissed and saved.evidence[0].quote == quote


def test_question_only_topic_does_not_become_explicit_requirement():
    from backend.app.schemas import Conversation, Segment
    from backend.app.workflow import analyse

    c = analyse(
        Conversation(
            id="q",
            title="Question",
            source="fixture",
            segments=[
                Segment(
                    id="s1",
                    speaker_id="A",
                    role="customer",
                    text="Can your ERP integration work?",
                )
            ],
        )
    )
    assert c.requirements[0].information_status == "inferred"
