"""Controlled graph with configurable semantic extraction and deterministic review checks."""

import re
from datetime import UTC, datetime
from time import perf_counter
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .claims import unsupported_claims
from .config import settings
from .knowledge import documents, domain_config, matches
from .reasoning import (
    PROMPT_VERSION,
    OllamaReasoningProvider,
    OpenAIReasoningProvider,
    add_catalogue_coverage_candidates,
    apply_extraction,
)
from .schemas import (
    Assessment,
    Conversation,
    Evidence,
    Finding,
    Observation,
    Requirement,
)


class State(TypedDict):
    conversation: dict


def evidence(s):
    return Evidence(
        segment_id=s.id,
        quote=s.text,
        speaker_role=s.role,
        start_ms=s.start_ms,
        end_ms=s.end_ms,
    )


def extract(c: Conversation):
    if settings.llm_provider in {"openai", "ollama"}:
        knowledge = documents(c.domain_id)
        provider = (
            OllamaReasoningProvider()
            if settings.llm_provider == "ollama"
            else OpenAIReasoningProvider()
        )
        result = provider.extract(c, knowledge)
        apply_extraction(c, result, knowledge)
        for req in c.requirements:
            req.extraction_origin = (
                "unclassified_review" if req.id.startswith("req-review-") else "model"
            )
        add_catalogue_coverage_candidates(c, knowledge)
        # Keep explicit questions and concerns visible even if the model only extracts needs.
        # These are wording matches with verbatim evidence, not inferred emotional states.
        for segment in c.segments:
            if segment.role != "customer":
                continue
            for kind, words in domain_config(c.domain_id)[
                "observation_patterns"
            ].items():
                if any(word in segment.text.casefold() for word in words) and not any(
                    o.kind == kind
                    and any(e.segment_id == segment.id for e in o.evidence)
                    for o in c.observations
                ):
                    c.observations.append(
                        Observation(
                            id=f"obs-wording-{kind}-{segment.id}",
                            kind=kind,
                            description=segment.text,
                            evidence=[evidence(segment)],
                        )
                    )
        return
    c.observations = []
    patterns = domain_config(c.domain_id)["observation_patterns"]
    for segment in c.segments:
        if segment.role != "customer":
            continue
        for kind, words in patterns.items():
            if any(word in segment.text.casefold() for word in words):
                c.observations.append(
                    Observation(
                        id=f"obs-{kind}-{segment.id}",
                        kind=kind,
                        description=segment.text,
                        evidence=[evidence(segment)],
                    )
                )
    c.requirements = []
    customer = [s for s in c.segments if s.role == "customer"]
    for d in documents(c.domain_id):
        if not d.get("capability_id"):
            continue
        hits = [s for s in customer if matches(s.text, d)]
        if not hits:
            continue
        c.requirements.append(
            Requirement(
                id="req-" + d["capability_id"],
                capability_id=d["capability_id"],
                title=d["requirement"],
                description=d["description"]
                + (
                    " Customer volume context: " + " ".join(s.text for s in hits)
                    if d["capability_id"] == "scale"
                    else ""
                ),
                original_description=d["description"]
                + (
                    " Customer volume context: " + " ".join(s.text for s in hits)
                    if d["capability_id"] == "scale"
                    else ""
                ),
                category=d["category"],
                priority="P0" if d["capability_id"] == "privacy" else "P1",
                confidence=0.65,
                information_status="inferred"
                if all(
                    "?" in item.text
                    and not any(
                        w in item.text.lower()
                        for w in ["need", "must", "chahiye", "चाहिए", "want"]
                    )
                    for item in hits
                )
                else "explicit",
                user_story="As a "
                + domain_config(c.domain_id)["user_persona"]
                + ", I want to "
                + d["requirement"].lower()
                + " so that the requested business workflow is clear and reviewable.",
                acceptance_criteria=d["criteria"],
                original_acceptance_criteria=d["criteria"],
                constraints=[d["excerpt"]] if d["capability_id"] == "privacy" else [],
                dependencies=d["dependencies"],
                open_questions=d["questions"],
                evidence=[evidence(s) for s in hits],
            )
        )
    # Preserve unrecognised customer statements as review items, rather than guessing semantics.
    known = {e.segment_id for r in c.requirements for e in r.evidence}
    for s in customer:
        if s.id not in known:
            c.requirements.append(
                Requirement(
                    id="req-review-" + s.id,
                    title="Clarify unclassified customer statement",
                    description=s.text,
                    original_description=s.text,
                    category="needs_review",
                    confidence=0.2,
                    information_status="inferred",
                    user_story="Pending human clarification.",
                    acceptance_criteria=[
                        "Confirm intended behaviour with the customer before approval."
                    ],
                    evidence=[evidence(s)],
                    open_questions=["What exact behaviour is requested here?"],
                )
            )


def assess(c):
    by_id = {
        d["capability_id"]: d for d in documents(c.domain_id) if d.get("capability_id")
    }
    c.assessments = []
    for r in c.requirements:
        d = by_id.get(r.capability_id)
        c.assessments.append(
            Assessment(
                requirement_id=r.id,
                status=d["status_value"] if d else "unknown",
                explanation=d["excerpt"]
                if d
                else "No approved source matches this statement; human clarification is required.",
                documentation_sources=[d["id"]] if d else [],
                dependencies=d["dependencies"] if d else [],
                clarification_questions=r.open_questions,
                risks=["Customer commitment requires review."]
                if not d or d["status_value"] != "supported"
                else [],
            )
        )

    if settings.llm_provider in {"ollama", "openai"}:
        from .technical import ground

        ground(c)


def sales(c):
    viable = {
        a.requirement_id
        for a in c.assessments
        if a.status in {"supported", "conditional"}
    }
    matched = [r for r in c.requirements if r.capability_id and r.id in viable]
    gaps = [a.explanation for a in c.assessments if a.status != "supported"]
    by_cap = {
        d["capability_id"]: d for d in documents(c.domain_id) if d.get("capability_id")
    }
    metadata = domain_config(c.domain_id)
    capabilities = {r.capability_id for r in matched}
    pitch = (
        " ".join(
            by_cap[r.capability_id].get(
                "pitch_hinglish", by_cap[r.capability_id]["excerpt"]
            )
            for r in matched
        )
        or "Aapka exact workflow aur constraints samajhna zaroori hai. Product fit abhi unknown hai."
    )
    configuration = next(
        (
            config["name"]
            for config in metadata["configurations"]
            if capabilities.intersection(config["match_any"])
        ),
        "Insufficient context for a configuration recommendation",
    )
    questions = [
        q
        for cap in metadata["next_question_priority"]
        if cap in capabilities
        for q in by_cap.get(cap, {}).get("questions", [])
    ]
    c.sales = {
        "product_name": configuration,
        "fit_reasons": [
            {
                "need_id": r.id,
                "reason": r.title,
                "sources": [by_cap[r.capability_id]["id"]],
            }
            for r in matched
            if by_cap[r.capability_id].get("recommendation_fit")
        ],
        "limitations": gaps,
        "sources": metadata["sources"],
        "pitch": pitch,
        "next_question": questions[0]
        if questions
        else "Which workflow and constraints should we clarify first?",
        "objection_handling": metadata["objection_response"],
        "escalation_required": bool(gaps),
        "escalation_reason": "Technical review needed for conditional or undocumented capabilities."
        if gaps
        else "Documented capabilities can be explained with sources.",
    }


def audit(c: Conversation):
    old = {f.id: f for f in c.findings}
    findings = []

    def add(fid, kind, description, ev, text, correction, severity="high"):
        f = Finding(
            id=fid,
            finding_type=kind,
            severity=severity,
            description=description,
            original_evidence=ev,
            downstream_text=text,
            suggested_correction=correction,
        )
        if fid in old and old[fid].downstream_text == text:
            f.reviewer_status = old[fid].reviewer_status
            f.reviewer_notes = old[fid].reviewer_notes
        findings.append(f)

    for s in c.segments:
        low = s.text.casefold()
        if (
            s.role == "sales"
            and unsupported_claims(s.text)
            and any(p in low for p in ["any erp", "every erp", "har erp", "हर ईआरपी"])
        ):
            add(
                "finding-erp-" + s.id,
                "unsupported_promise",
                "Universal ERP compatibility is not supported by the approved integration documentation.",
                [evidence(s)],
                s.text,
                "ERP integration depends on API availability, compatibility, authentication, field mapping and sandbox validation. [kb-erp]",
            )
        if (
            s.role == "sales"
            and "every partner" in low
            and "complete history" in low
            and c.domain_id == "synthetic-device-lifecycle"
        ):
            add(
                "finding-partner-" + s.id,
                "constraint_loss",
                "Unrestricted partner access conflicts with the customer’s privacy constraint.",
                [
                    evidence(x)
                    for x in c.segments
                    if x.role == "customer"
                    and matches(
                        x.text,
                        next(
                            d for d in documents(c.domain_id) if d["id"] == "kb-privacy"
                        ),
                    )
                ],
                s.text,
                "Partners see assigned service records only. Owner personal information remains hidden. [kb-privacy]",
            )
        elif (
            s.role == "sales"
            and unsupported_claims(s.text)
            and c.domain_id == "marketplace"
        ):
            add(
                "finding-promise-" + s.id,
                "unsupported_promise",
                "The sales statement includes a guarantee that is not established by the approved marketplace documentation.",
                [evidence(s)],
                s.text,
                "Describe the documented candidate approach, preserve data and evaluation dependencies, and remove unverified accuracy, conversion or delivery guarantees. [kb-market-playbook]",
            )
    for capability in ["privacy", "scale"]:
        d = next(
            (d for d in documents(c.domain_id) if d.get("capability_id") == capability),
            None,
        )
        if not d:
            continue
        hits = [s for s in c.segments if s.role == "customer" and matches(s.text, d)]
        if len(hits) > 1 and any(
            w in hits[-1].text.lower()
            for w in ["actually", "instead", "now", "पहले", "अब", "badal"]
        ):
            add(
                "finding-revision-" + capability,
                "contradictory",
                "Customer wording suggests a changed or conflicting "
                + capability
                + " requirement. Confirm the latest intent.",
                [evidence(s) for s in hits],
                hits[-1].text,
                "Ask the customer which statement supersedes the earlier one and preserve both quotes.",
                "medium",
            )
    for r in c.requirements:
        d = next(
            (
                d
                for d in documents(c.domain_id)
                if d.get("capability_id") == r.capability_id
            ),
            None,
        )
        if d and r.description != r.original_description:
            if r.capability_id == "privacy" and not all(
                w in r.description.lower() for w in ["personal", "hidden"]
            ):
                add(
                    "finding-edit-" + r.id,
                    "constraint_loss",
                    "Edited requirement may have lost the original-owner privacy restriction.",
                    r.evidence,
                    r.description,
                    r.original_description,
                )
            else:
                add(
                    "finding-edit-" + r.id,
                    "altered",
                    "Requirement wording was revised; verify that scope and conditions remain faithful.",
                    r.evidence,
                    r.description,
                    "Compare the edit to the original quote and record a customer-confirmed reason.",
                    "medium",
                )
        if r.original_acceptance_criteria and not set(
            r.original_acceptance_criteria
        ).issubset(r.acceptance_criteria):
            add(
                "finding-criteria-" + r.id,
                "constraint_loss",
                "PM acceptance criteria changed or lost an original check; verify intent before approval.",
                r.evidence,
                "\n".join(r.acceptance_criteria),
                "\n".join(r.original_acceptance_criteria),
                "high" if r.capability_id == "privacy" else "medium",
            )
        if r.supersedes and r.information_status != "explicit":
            add(
                "finding-refinement-" + r.id,
                "unverified_assumption",
                "PM-refined scope needs customer confirmation.",
                r.evidence,
                r.description,
                "Confirm the refinement with the customer and record the confirmation before accepting it.",
                "medium",
            )
        if r.information_status == "assumption":
            add(
                "finding-assumption-" + r.id,
                "unverified_assumption",
                "An assumption remains unverified.",
                r.evidence,
                r.description,
                "Ask the customer to confirm this assumption.",
                "medium",
            )
        if r.pm_status in ["rejected", "deferred"] and not r.superseded_by:
            add(
                "finding-omission-" + r.id,
                "omitted",
                "A customer need was excluded from the current handoff.",
                r.evidence,
                r.description,
                "Explicitly explain the exclusion and confirm with the customer.",
                "medium",
            )
    if c.response:
        for a in c.assessments:
            r = next(r for r in c.requirements if r.id == a.requirement_id)
            if a.status == "conditional" and not caveat_present(
                c.response.text, r.capability_id
            ):
                add(
                    "finding-response-" + r.id,
                    "caveat_loss",
                    "Customer response lacks the required condition.",
                    r.evidence,
                    c.response.text,
                    a.explanation,
                )
    if c.semantic_audit:
        from .semantic import fingerprint

        if c.semantic_audit.get("fingerprint") == fingerprint(c):
            for raw in c.semantic_audit.get("findings", []):
                finding = Finding.model_validate(raw)
                if finding.id in old:
                    finding.reviewer_status = old[finding.id].reviewer_status
                    finding.reviewer_notes = old[finding.id].reviewer_notes
                findings.append(finding)
        else:
            c.semantic_audit = None
    c.findings = findings


def caveat_present(text, capability):
    t = text.lower()
    if capability == "erp":
        if re.search(
            r"(?:no|without)\s+(?:an?\s+)?api|compatibility\s+(?:is\s+)?not\s+required|no\s+compatibility",
            t,
        ):
            return False
        return (
            "erp" in t
            and any(x in t for x in ["compatibility", "संगतता"])
            and any(x in t for x in ["api", "एपीआई"])
        )
    if capability == "privacy":
        if re.search(
            r"not\s+(?:hidden|private|protected)|hidden\s+(?:nahi|nahin)|नहीं\s+छिप|निजी\s+नहीं",
            t,
        ):
            return False
        return (
            any(x in t for x in ["personal", "व्यक्तिगत"])
            and any(
                x in t
                for x in [
                    "hidden",
                    "never original-owner",
                    "exclude personal",
                    "नहीं दिखे",
                    "निजी",
                ]
            )
            and any(x in t for x in ["test", "परीक्षण"])
        )
    return any(x in t for x in ["depend", "conditional", "शर्त", "निर्भर", "जरूरी"])


def signals(c):
    c.signals = [
        {
            "id": "signal-" + observation.id,
            "label": observation.description,
            "kind": "linguistic",
            "evidence": [ev.model_dump() for ev in observation.evidence],
            "confidence": observation.confidence,
            "caveat": "Model candidate grounded in expressed words; not an internal-emotion diagnosis. Audio energy and pauses are separate observations.",
        }
        for observation in c.observations
        if observation.kind == "sentiment" and not observation.dismissed
    ]
    for s in c.segments:
        if s.role != "customer":
            continue
        if any(
            observation.kind == "sentiment"
            and any(ev.segment_id == s.id for ev in observation.evidence)
            for observation in c.observations
        ):
            continue
        if "?" in s.text or any(
            w in s.text.lower()
            for w in ["concern", "चिंता", "pakka", "confus", "महंगा", "expensive"]
        ):
            c.signals.append(
                {
                    "id": "signal-" + s.id,
                    "label": "Expressed concern / clarification request",
                    "kind": "linguistic",
                    "evidence": [evidence(s).model_dump()],
                    "confidence": 0.55,
                    "caveat": "Keyword-based observation of wording; not a claim about internal emotion. Acoustic analysis has not been performed.",
                }
            )


def run_node(name, fn):
    def node(state):
        c = Conversation.model_validate(state["conversation"])
        start = perf_counter()
        if c.status == "analysing":
            from . import store

            c.processing_step = name
            store.save(c)
        fn(c)
        c.node_runs.append(
            {
                "node": name,
                "status": "completed",
                "provider": settings.llm_provider + "/" + settings.llm_model
                if name == "semantic_requirement_extraction"
                and settings.llm_provider in {"openai", "ollama"}
                else "deterministic-demo",
                "schema_version": "1",
                "prompt_version": PROMPT_VERSION
                if name == "semantic_requirement_extraction"
                and settings.llm_provider in {"openai", "ollama"}
                else "rules-v1",
                "duration_ms": round((perf_counter() - start) * 1000, 2),
                "at": datetime.now(UTC).isoformat(),
            }
        )
        return {"conversation": c.model_dump(mode="json")}

    return node


def build_graph():
    g = StateGraph(State)
    nodes = [
        ("semantic_requirement_extraction", extract),
        ("technical_context_and_feasibility", assess),
        ("grounded_sales_strategy", sales),
        ("communication_signals", signals),
        ("intent_integrity_audit", audit),
    ]
    prev = START
    for name, fn in nodes:
        g.add_node(name, run_node(name, fn))
        g.add_edge(prev, name)
        prev = name
    g.add_edge(prev, END)
    return g.compile()


graph = build_graph()


def analyse(c: Conversation) -> Conversation:
    c.response = None
    result = graph.invoke({"conversation": c.model_dump(mode="json")})
    return Conversation.model_validate(result["conversation"])
