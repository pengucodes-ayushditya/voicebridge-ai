"""Run the fixed synthetic conversation through the configured reasoning graph."""

import json
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import ROOT, settings
from backend.app.schemas import Conversation
from backend.app.workflow import analyse


def main():
    raw = json.loads((ROOT / "data/canonical.json").read_text())
    start = perf_counter()
    c = analyse(
        Conversation(
            id="local-preflight",
            title=raw["title"],
            source="Synthetic preflight fixture",
            segments=raw["segments"],
        )
    )
    segments = {s.id: s for s in c.segments}
    valid = all(
        e.segment_id in segments
        and e.quote in segments[e.segment_id].text
        and segments[e.segment_id].role == "customer"
        for r in c.requirements
        for e in r.evidence
    )
    actual = {r.capability_id for r in c.requirements if r.capability_id}
    expected = {"qr", "repair", "privacy", "erp", "scale"}
    report = {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "duration_seconds": round(perf_counter() - start, 2),
        "synthetic": True,
        "requirements": len(c.requirements),
        "evidence_valid": valid,
        "capabilities": sorted(actual),
        "capability_origins": {r.capability_id: r.extraction_origin for r in c.requirements if r.capability_id},
        "missing_canonical_capabilities": sorted(expected - actual),
        "extra_capabilities": sorted(actual - expected),
        "node_runs": c.node_runs,
        "limitation": "Single authored synthetic case; not independent multilingual quality validation.",
    }
    path = ROOT / "outputs" / "local-reasoning-preflight.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
