"""One workflow state contract shared by the guided UI and exports."""

from .config import settings
from .semantic import fingerprint


def describe(c):
    processing = c.status not in {"ready", "failed"}
    unassigned = [s.id for s in c.segments if s.role == "unknown"]
    active = [
        r
        for r in c.requirements
        if r.pm_status not in {"rejected", "deferred"} and not r.superseded_by
    ]
    pm = [r for r in active if r.pm_status != "accepted"]
    assessment = {a.requirement_id: a for a in c.assessments}
    tech = [
        r
        for r in active
        if r.id not in assessment or assessment[r.id].reviewer_status != "approved"
    ]
    high = [
        f
        for f in c.findings
        if f.severity == "high" and f.reviewer_status not in {"resolved", "dismissed"}
    ]
    model_enabled = settings.llm_provider in {"ollama", "openai"}
    audited = bool(
        c.semantic_audit and c.semantic_audit.get("fingerprint") == fingerprint(c)
    )
    blockers = []
    if c.status == "failed":
        blockers.append(
            {
                "stage": "conversation",
                "code": "failed",
                "label": "Processing failed. Review the error and retry analysis.",
            }
        )
    if processing:
        blockers.append(
            {
                "stage": "conversation",
                "code": "processing",
                "label": "Wait for the current processing step to finish.",
            }
        )
    if unassigned:
        blockers.append(
            {
                "stage": "conversation",
                "code": "speakers",
                "label": f"Assign roles to {len(unassigned)} transcript turns before relying on the analysis.",
            }
        )
    if not c.node_runs:
        blockers.append(
            {
                "stage": "conversation",
                "code": "analysis",
                "label": "Analyse the reviewed conversation to extract customer needs.",
            }
        )
    for r in pm:
        blockers.append(
            {
                "stage": "requirements",
                "code": "pm",
                "item_id": r.id,
                "label": "Review scope: " + r.title,
            }
        )
    for r in tech:
        if r not in pm:
            blockers.append(
                {
                    "stage": "engineering",
                    "code": "engineering",
                    "item_id": r.id,
                    "label": "Review technical assessment: " + r.title,
                }
            )
    for finding in high:
        blockers.append(
            {
                "stage": "response",
                "code": "finding",
                "item_id": finding.id,
                "label": "Resolve a high-priority integrity finding: "
                + finding.finding_type.replace("_", " "),
            }
        )
    if not active and c.node_runs:
        blockers.append(
            {
                "stage": "requirements",
                "code": "scope",
                "label": "Confirm at least one active customer requirement before drafting a commitment.",
            }
        )
    can_draft = bool(
        active
        and not pm
        and not tech
        and not high
        and c.status == "ready"
        and not unassigned
    )
    if c.response and model_enabled and not audited:
        blockers.append(
            {
                "stage": "response",
                "code": "audit",
                "label": "Run the intent audit on the exact saved response before approval.",
            }
        )
    steps = [
        {
            "id": "conversation",
            "label": "Conversation",
            "state": "processing"
            if processing
            else "attention"
            if unassigned or not c.node_runs
            else "complete",
        },
        {
            "id": "sales",
            "label": "Sales Copilot",
            "state": "complete"
            if c.sales.get("pitch_reviewed")
            else "ready"
            if c.sales
            else "waiting",
        },
        {
            "id": "requirements",
            "label": "Requirements",
            "state": "attention" if pm else "complete" if active else "waiting",
        },
        {
            "id": "engineering",
            "label": "Engineering",
            "state": "waiting"
            if pm or not active
            else "attention"
            if tech
            else "complete",
        },
        {
            "id": "response",
            "label": "Customer response",
            "state": "complete"
            if c.response and c.response.approved
            else "ready"
            if can_draft
            else "waiting",
        },
    ]
    next_stage = (
        blockers[0]["stage"]
        if blockers
        else "sales"
        if not c.sales.get("pitch_reviewed")
        else "response"
    )
    return {
        "conversation_id": c.id,
        "version": c.version,
        "steps": steps,
        "blockers": blockers,
        "next_stage": next_stage,
        "can_draft": can_draft,
        "can_approve": bool(
            can_draft and c.response and (audited or not model_enabled)
        ),
        "audit_current": audited,
        "model_audit_required": model_enabled,
        "can_generate_audio": bool(can_draft and c.response and c.response.approved),
    }
