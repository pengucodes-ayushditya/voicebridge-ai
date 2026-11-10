import asyncio
import json

import httpx
import pytest

from backend.app.providers import GnaniProvider, MissingCredentials, ProviderError


def test_missing_key_fails_without_fixture_substitution():
    with pytest.raises(MissingCredentials):
        asyncio.run(GnaniProvider(key="").status("job"))


def test_batch_lifecycle_and_signed_download(tmp_path):
    requests = []

    def handler(r):
        requests.append(r)
        if r.url.host == "storage.amazonaws.com":
            assert "x-api-key-id" not in r.headers
            return httpx.Response(
                200,
                json={
                    "segments": [
                        {
                            "speaker_id": 0,
                            "start_time": 1.2,
                            "end_time": 3.4,
                            "text": "Hello",
                            "language_detected": "en-IN",
                        }
                    ]
                },
            )
        assert r.headers["x-api-key-id"] == "test-key"
        if r.method == "POST" and r.url.path.endswith("/jobs"):
            assert b"with_diarization" in r.content and b"codemix" in r.content
            return httpx.Response(201, json={"job_id": "abc"})
        if r.url.path.endswith("/start"):
            return httpx.Response(200, json={"status": "QUEUED"})
        if r.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "transcript_url": "https://storage.amazonaws.com/transcript.json"
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"status": "COMPLETED"})

    p = GnaniProvider(key="test-key", transport=httpx.MockTransport(handler))
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"RIFF")

    async def run():
        assert await p.create_job(audio) == "abc"
        await p.start("abc")
        assert await p.status("abc") == "COMPLETED"
        segments = await p.result("abc")
        assert segments[0].start_ms == 1200
        assert segments[0].speaker_id == "0"
        assert segments[0].role == "unknown"

    asyncio.run(run())
    assert len(requests) == 5


def test_timbre_payload_and_binary_response():
    def handler(r):
        d = json.loads(r.content)
        assert d["model"] == "timbre-v3.0"
        assert d["voice"] == "Shivani"
        assert d["language"] == "hi-en"
        assert d["audio_config"]["container"] == "wav"
        return httpx.Response(200, content=b"RIFFdemo")

    assert (
        asyncio.run(
            GnaniProvider(key="x", transport=httpx.MockTransport(handler)).speak(
                "Reviewed text", "Hinglish"
            )
        )
        == b"RIFFdemo"
    )


def test_403_is_actionable():
    p = GnaniProvider(
        key="x", transport=httpx.MockTransport(lambda r: httpx.Response(403))
    )
    with pytest.raises(ProviderError, match="403"):
        asyncio.run(p.status("abc"))


def test_duplicate_provider_segment_ids_and_empty_segments():
    result = GnaniProvider.normalise(
        {
            "segments": [
                {"segment_id": 0, "text": "a", "speaker_id": 1},
                {"segment_id": 0, "text": "b", "speaker_id": 2},
                {"text": ""},
            ]
        }
    )
    assert len({s.id for s in result}) == 2
    assert result[0].start_ms is None


def test_rest_transcript_preserves_missing_speaker_and_timestamps():
    import asyncio
    import tempfile
    from pathlib import Path

    from backend.app.config import settings

    def handler(request):
        assert request.url.path == "/stt/v3"
        assert b"prisma-v3.0" in request.content
        return httpx.Response(
            200,
            json={
                "success": True,
                "model": settings.gnani_stt_model,
                "transcript": "हमें QR चाहिए।",
                "detected_language_code": "hi-IN",
            },
        )

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "synthetic.wav"
        path.write_bytes(b"fixture")
        result = asyncio.run(
            GnaniProvider(
                key="test-key", transport=httpx.MockTransport(handler)
            ).transcribe_short(path)
        )
    assert result[0].role == "unknown" and result[0].speaker_id == "unknown"
    assert result[0].start_ms is None and result[0].end_ms is None
    assert result[0].text == "हमें QR चाहिए।"
