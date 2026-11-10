import json
import re

from .config import ROOT


def documents(domain_id: str | None = None) -> list[dict]:
    from .knowledge_admin import all_sources

    docs = (
        json.loads((ROOT / "data/knowledge.json").read_text())
        + json.loads((ROOT / "data/marketplace-knowledge.json").read_text())
        + [d for d in all_sources() if d.get("status") == "approved"]
    )
    return [
        d
        for d in docs
        if domain_id is None
        or d.get("domain_id", "synthetic-device-lifecycle") == domain_id
    ]


def matches(text: str, doc: dict) -> bool:
    low = text.casefold()
    return any(
        (
            bool(re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", low))
            if k.isascii() and " " not in k
            else k in low
        )
        for k in doc.get("keywords", [])
    )


def retrieve(query: str, domain_id: str = "synthetic-device-lifecycle") -> list[dict]:
    return [
        d
        for d in documents(domain_id)
        if d["status"] == "approved" and matches(query, d)
    ]


def answer(query: str, domain_id: str = "synthetic-device-lifecycle") -> dict:
    hits = retrieve(query, domain_id)
    if not hits:
        return {
            "status": "unknown",
            "answer": "This is not documented in the approved synthetic knowledge base. Ask a product specialist before making a commitment.",
            "sources": [],
            "escalation_required": True,
        }
    status = (
        "conditional"
        if any(d.get("status_value") == "conditional" for d in hits)
        else (
            "unknown"
            if any(d.get("status_value") == "unknown" for d in hits)
            else (
                "unsupported"
                if any(d.get("status_value") == "unsupported" for d in hits)
                else "supported"
            )
        )
    )
    return {
        "status": status,
        "answer": "\n\n".join(d["excerpt"] for d in hits),
        "sources": [d["id"] for d in hits],
        "escalation_required": status != "supported",
    }


def domain_config(domain_id: str = "synthetic-device-lifecycle") -> dict:
    base = json.loads((ROOT / "data/domain.json").read_text())
    if domain_id == "marketplace":
        base.update(json.loads((ROOT / "data/marketplace-domain.json").read_text()))
    return base
