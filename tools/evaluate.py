"""Run the curated synthetic rule-engine evaluation; no live-model claims."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import ROOT, settings
from backend.app.schemas import Conversation, Segment
from backend.app.workflow import analyse


def evaluate():
    # This report is a deterministic baseline, regardless of the application .env.
    settings.llm_provider = "deterministic-demo"
    cases = json.loads((ROOT / "data/evaluation.json").read_text())
    rows = []
    tp = fp = fn = grounded = total = status_correct = status_total = (
        promise_correct
    ) = 0
    for case in cases:
        c = analyse(
            Conversation(
                id=case["id"],
                title=case["id"],
                source="Synthetic evaluation fixture",
                segments=[
                    Segment(id=f"s{i}", speaker_id=role, role=role, text=text)
                    for i, (role, text) in enumerate(case["turns"])
                ],
            )
        )
        actual = {r.capability_id for r in c.requirements if r.capability_id}
        expected = set(case["capabilities"])
        tp += len(actual & expected)
        fp += len(actual - expected)
        fn += len(expected - actual)
        for r in c.requirements:
            total += 1
            grounded += bool(
                r.evidence
                and all(
                    any(s.id == e.segment_id and s.text == e.quote for s in c.segments)
                    for e in r.evidence
                )
            )
        statuses = {
            r.capability_id: next(
                a.status for a in c.assessments if a.requirement_id == r.id
            )
            for r in c.requirements
        }
        for key, value in case["statuses"].items():
            status_total += 1
            status_correct += statuses.get(key) == value
        promise = any(f.finding_type == "unsupported_promise" for f in c.findings)
        promise_correct += promise == case["promise"]
        rows.append(
            {
                "id": case["id"],
                "expected": sorted(expected),
                "actual": sorted(actual),
                "capability_match": actual == expected,
                "statuses_match": all(
                    statuses.get(k) == v for k, v in case["statuses"].items()
                ),
                "promise_match": promise == case["promise"],
            }
        )
    report = {
        "case_count": len(cases),
        "engine": "deterministic-demo",
        "capability_precision": tp / (tp + fp) if tp + fp else None,
        "capability_recall": tp / (tp + fn) if tp + fn else None,
        "feasibility_correct": status_correct,
        "feasibility_total": status_total,
        "requirements_with_valid_evidence": grounded,
        "requirement_count": total,
        "universal_erp_promise_cases_correct": promise_correct,
        "cases": rows,
        "limitations": [
            "Curated synthetic keyword/template cases authored alongside this implementation; not independent validation.",
            "Capability presence is evaluated, not semantic requirement quality or true multilingual comprehension.",
            "This report evaluates text rules only. Separate live-call reports record provider verification, not independent speech quality.",
            "This deterministic report does not score the separate qualitative single-model summary. No real-world sales, productivity or causal conclusions follow.",
        ],
    }
    target = ROOT / "outputs/evaluation-results.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ["cases", "limitations"]},
            indent=2,
        )
    )
    return report


if __name__ == "__main__":
    evaluate()
