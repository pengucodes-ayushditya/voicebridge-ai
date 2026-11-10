from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_end_to_end_persistent_demo_and_stale_write():
    c = client.post("/api/conversations/demo").json()
    cid = c["id"]
    assert len(c["requirements"]) == 5 and len(c["findings"]) == 2
    assert client.get("/api/conversations/" + cid).json()["title"] == c["title"]
    assert client.get("/api/conversations/" + cid + "/handoff").status_code == 200
    r = client.post(
        "/api/conversations/" + cid + "/review",
        json={"version": c["version"], "action": "audit"},
    )
    assert r.status_code == 200
    stale = client.post(
        "/api/conversations/" + cid + "/review",
        json={"version": c["version"], "action": "audit"},
    )
    assert stale.status_code == 409
    assert client.delete("/api/conversations/" + cid).json()["deleted"]


def test_upload_missing_credentials():
    r = client.post(
        "/api/conversations/upload",
        data={"synthetic_consent": "true"},
        files={"file": ("a.wav", b"RIFF", "audio/wav")},
    )
    assert r.status_code == 503 and "credentials" in r.json()["detail"]


def test_transcript_correction_resets_reviews_and_preserves_original():
    c = client.post("/api/conversations/demo").json()
    ss = c["segments"]
    ss[0]["text"] = "We need QR history with authorised access."
    r = client.patch(
        "/api/conversations/" + c["id"] + "/transcript",
        json={
            "version": c["version"],
            "segments": ss,
            "reason": "Corrected transcription",
        },
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["segments"][0]["original_text"] != ss[0]["text"]
    assert updated["original_segments"][0]["text"] == c["original_segments"][0]["text"]
    assert all(a["reviewer_status"] == "pending" for a in updated["assessments"])


def test_training_three_turns_and_actual_quotes():
    s = client.post("/api/training/sessions", json={"scenario_id": "technical"}).json()
    for text in [
        "We support any ERP.",
        "I understand your concern. Which API is available?",
        "We should validate compatibility and protect owner personal data.",
    ]:
        r = client.post(
            "/api/training/sessions/" + s["id"] + "/turns", json={"text": text}
        )
        assert r.status_code == 200
        s = r.json()
    assert s["complete"] and len(s["evaluation"]["rubric"]) == 8
    assert "We support any ERP." in s["evaluation"]["flagged_claims"]
    assert s["evaluation"]["examples"][0]["quote"] == "We support any ERP."


def test_health_and_unknown_ids():
    r = client.get("/api/health")
    assert r.status_code == 200 and "x-request-id" in r.headers
    assert client.get("/api/conversations/missing").status_code == 404


def test_provider_status_reports_configured_reasoning_without_claiming_verified(
    monkeypatch,
):
    from backend.app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "test-model")
    result = client.get("/api/providers/status").json()["reasoning"]
    assert result["provider"] == "openai"
    assert result["model"] == "test-model"
    assert result["configured"] is True
    assert result["verified"] is False
    assert "test-key" not in str(result)


def test_full_http_review_flow_and_missing_timbre_key():
    c = client.post("/api/conversations/demo").json()
    base = "/api/conversations/" + c["id"]

    def action(kind, role, item=None, changes=None):
        nonlocal c
        r = client.post(
            base + "/review",
            json={
                "version": c["version"],
                "action": kind,
                "item_id": item,
                "changes": changes or {},
                "reason": "Reviewed synthetic evidence and documented caveats.",
            },
            headers={"X-Demo-Role": role},
        )
        assert r.status_code == 200, r.text
        c = r.json()

    for r in list(c["requirements"]):
        action("pm", "Product Manager", r["id"], {"pm_status": "accepted"})
        action(
            "engineering",
            "Technical Reviewer",
            r["id"],
            {"reviewer_status": "approved"},
        )
    for f in list(c["findings"]):
        action(
            "finding", "Technical Reviewer", f["id"], {"reviewer_status": "resolved"}
        )
    action("draft", "Sales Representative", changes={"language": "Hinglish"})
    action("response", "Sales Representative", changes={"approved": True})
    assert c["response"]["approved"] and "compatibility" in c["response"]["text"]
    assert (
        client.post(
            base + "/audio", headers={"X-Demo-Role": "Sales Representative"}
        ).status_code
        == 503
    )
    assert client.get(base + "/audio").status_code == 404
