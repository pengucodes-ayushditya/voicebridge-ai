"""Historical successful provider-call metadata, bound to account and model."""

import hashlib
import json
from datetime import UTC, datetime

from .config import ROOT, settings

PATH = ROOT / "work" / "provider-verification.json"


def account_id(key):
    return hashlib.sha256((settings.gnani_base_url + key).encode()).hexdigest()


def record_success(kind, model, key, voice=None):
    if not key or key != settings.gnani_api_key_id:
        return
    try:
        records = json.loads(PATH.read_text()) if PATH.exists() else {}
    except (ValueError, OSError):
        records = {}
    records[kind] = {
        "model": model,
        "voice": voice,
        "account": account_id(key),
        "at": datetime.now(UTC).isoformat(),
    }
    temp = PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(records))
    temp.replace(PATH)


def success(kind, model, voice=None):
    try:
        record = json.loads(PATH.read_text()).get(kind, {})
    except (ValueError, OSError):
        return None
    return (
        record.get("at")
        if record.get("account") == account_id(settings.gnani_api_key_id)
        and record.get("model") == model
        and record.get("voice") == voice
        else None
    )


def reasoning_identity():
    base = (
        settings.ollama_base_url
        if settings.llm_provider == "ollama"
        else settings.openai_base_url
    )
    return hashlib.sha256(
        (
            settings.llm_provider + base + settings.llm_model + settings.llm_api_key
        ).encode()
    ).hexdigest()


def record_reasoning_success():
    path = ROOT / "work" / "reasoning-verification.json"
    path.write_text(
        json.dumps(
            {"identity": reasoning_identity(), "at": datetime.now(UTC).isoformat()}
        )
    )


def reasoning_success():
    try:
        record = json.loads((ROOT / "work" / "reasoning-verification.json").read_text())
    except (ValueError, OSError):
        return None
    return record.get("at") if record.get("identity") == reasoning_identity() else None
