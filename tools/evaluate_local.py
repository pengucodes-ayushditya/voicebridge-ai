"""Repeat the authored local-model capability evaluation; no independent quality claim."""

import json
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import ROOT, settings
from backend.app.schemas import Conversation, Segment
from backend.app.workflow import analyse


def main():
    if settings.llm_provider != "ollama":
        raise SystemExit(
            "This runner requires LLM_PROVIDER=ollama. Use tools/evaluate.py for deterministic evaluation."
        )
    cases = json.loads((ROOT / "data/evaluation.json").read_text())
    rows = []
    start = perf_counter()
    for case in cases:
        c = analyse(
            Conversation(
                id=case["id"],
                title=case["id"],
                source="Authored synthetic evaluation",
                segments=[
                    Segment(id=f"s{i}", speaker_id=role, role=role, text=text)
                    for i, (role, text) in enumerate(case["turns"])
                ],
            )
        )
        actual = {r.capability_id for r in c.requirements if r.capability_id}
        expected = set(case["capabilities"])
        rows.append(
            {
                "id": case["id"],
                "expected": sorted(expected),
                "actual": sorted(actual),
                "missing": sorted(expected - actual),
                "extra": sorted(actual - expected),
                "origins": {
                    r.capability_id: r.extraction_origin
                    for r in c.requirements
                    if r.capability_id
                },
                "feasibility": {
                    r.capability_id: next(
                        a.status for a in c.assessments if a.requirement_id == r.id
                    )
                    for r in c.requirements
                    if r.capability_id
                },
                "evidence_valid": all(
                    any(
                        s.id == e.segment_id
                        and e.quote in s.text
                        and s.role == "customer"
                        for s in c.segments
                    )
                    for r in c.requirements
                    for e in r.evidence
                ),
            }
        )
        report = {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "completed_cases": len(rows),
            "total_cases": len(cases),
            "duration_seconds": round(perf_counter() - start, 2),
            "technical_source_entailment_included": True,
            "cases": rows,
            "limitations": [
                "Authored synthetic cases, not blind validation. Capability labels do not establish full intent preservation.",
                "Catalogue coverage candidates are inferred and require confirmation.",
                "Technical source entailment is a conservative model candidate with human review.",
            ],
        }
        (ROOT / "outputs/local-model-evaluation.json").write_text(
            json.dumps(report, indent=2)
        )
        print(f"{len(rows)}/{len(cases)}: {case['id']}", flush=True)


if __name__ == "__main__":
    main()
