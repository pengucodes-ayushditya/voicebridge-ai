import json

import httpx
import pytest

from backend.app.knowledge import documents
from backend.app.reasoning import (
    ExtractionResult,
    OpenAIReasoningProvider,
    ReasoningError,
    apply_extraction,
)
from backend.app.schemas import Conversation, Segment


def conversation():
    return Conversation(
        id="reasoning-test",
        title="Synthetic extraction test",
        source="test fixture",
        segments=[
            Segment(
                id="customer-1",
                speaker_id="A",
                role="customer",
                text="We need a QR for every device.",
            ),
            Segment(
                id="sales-1", speaker_id="B", role="sales", text="QR is supported."
            ),
            Segment(
                id="customer-2",
                speaker_id="A",
                role="customer",
                text="Can your system work offline?",
            ),
        ],
    )


def api_response(payload, status="completed"):
    return {
        "status": status,
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(payload)}],
            }
        ],
    }


def item(
    segment_id,
    quote,
    *,
    kind="need",
    capability_id=None,
    description="Customer statement",
):
    return {
        "kind": kind,
        "segment_id": segment_id,
        "quote": quote,
        "description": description,
        "capability_id": capability_id,
        "information_status": "explicit",
        "confidence": 0.8,
    }


def test_responses_request_uses_strict_schema_and_validates_result():
    sent = {}

    def handler(request):
        sent["request"] = request
        sent["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json=api_response(
                {
                    "items": [
                        item(
                            "customer-1",
                            "We need a QR for every device.",
                            capability_id="qr",
                        )
                    ]
                }
            ),
        )

    provider = OpenAIReasoningProvider(
        api_key="test-secret",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )
    result = provider.extract(conversation(), documents())

    assert len(result.items) == 1
    assert sent["request"].headers["Authorization"] == "Bearer test-secret"
    assert sent["body"]["model"] == "test-model"
    assert sent["body"]["text"]["format"]["strict"] is True
    assert sent["body"]["text"]["format"]["schema"]["additionalProperties"] is False


@pytest.mark.parametrize("status", ["incomplete", "failed"])
def test_noncompleted_response_is_rejected(status):
    provider = OpenAIReasoningProvider(
        api_key="test-secret",
        model="test-model",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=api_response({"items": []}, status))
        ),
    )
    with pytest.raises(ReasoningError, match="incomplete or refused"):
        provider.extract(conversation(), documents())


def test_provider_http_error_does_not_expose_response_body():
    provider = OpenAIReasoningProvider(
        api_key="test-secret",
        model="test-model",
        transport=httpx.MockTransport(
            lambda _: httpx.Response(403, text="sensitive provider detail")
        ),
    )
    with pytest.raises(ReasoningError) as exc:
        provider.extract(conversation(), documents())
    assert "sensitive provider detail" not in str(exc.value)
    assert "test-secret" not in str(exc.value)


def test_missing_config_fails_before_network_call():
    provider = OpenAIReasoningProvider(api_key="", model="")
    with pytest.raises(ReasoningError, match="LLM_API_KEY or LLM_MODEL"):
        provider.extract(conversation(), documents())


def test_mapper_rejects_sales_and_invalid_quotes_and_keeps_unknown_needs_for_review():
    c = conversation()
    result = ExtractionResult.model_validate(
        {
            "items": [
                item(
                    "customer-1", "We need a QR for every device.", capability_id="qr"
                ),
                item("sales-1", "QR is supported.", capability_id="qr"),
                item("customer-2", "invented quote", capability_id="offline"),
                item(
                    "customer-2",
                    "Can your system work offline?",
                    kind="question",
                    description="Offline support question",
                ),
            ]
        }
    )

    apply_extraction(c, result, documents())

    mapped = next(r for r in c.requirements if r.capability_id == "qr")
    assert mapped.evidence[0].segment_id == "customer-1"
    assert all(e.speaker_role == "customer" for r in c.requirements for e in r.evidence)
    review = next(r for r in c.requirements if r.id == "req-review-customer-2")
    assert review.capability_id is None
    assert review.information_status == "inferred"
    assert any(o.description == "Offline support question" for o in c.observations)


def test_openai_adapter_is_connected_to_analysis_graph(monkeypatch):
    from backend.app import workflow

    class StubProvider:
        def extract(self, c, approved_knowledge):
            return ExtractionResult.model_validate(
                {
                    "items": [
                        item(
                            "customer-1",
                            "We need a QR for every device.",
                            capability_id="qr",
                        )
                    ]
                }
            )

    monkeypatch.setattr(workflow.settings, "llm_provider", "openai")
    monkeypatch.setattr(workflow.settings, "llm_model", "test-model")
    monkeypatch.setattr(workflow, "OpenAIReasoningProvider", StubProvider)
    result = workflow.analyse(conversation())

    requirement = next(r for r in result.requirements if r.capability_id == "qr")
    run = next(
        n for n in result.node_runs if n["node"] == "semantic_requirement_extraction"
    )
    assert requirement.evidence[0].quote == "We need a QR for every device."
    assert run["provider"] == "openai/test-model"
    assert run["prompt_version"] == "semantic-extraction-v3"


def test_ollama_structured_extraction(monkeypatch):
    from backend.app.config import settings
    from backend.app.reasoning import OllamaReasoningProvider

    monkeypatch.setattr(settings, "llm_model", "local-test")

    def handler(request):
        payload = json.loads(request.content)
        assert payload["model"] == "local-test"
        assert payload["stream"] is False
        assert payload["format"]["additionalProperties"] is False
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": "stop",
                "message": {"content": '{"items": []}'},
            },
        )

    result = OllamaReasoningProvider(transport=httpx.MockTransport(handler)).extract(
        conversation(), documents()
    )
    assert result.items == []


@pytest.mark.parametrize(
    "raw",
    [
        {"done": False, "message": {"content": '{"items": []}'}},
        {
            "done": True,
            "done_reason": "length",
            "message": {"content": '{"items": []}'},
        },
        {"done": True, "message": {"content": "invalid json"}},
    ],
)
def test_ollama_rejects_incomplete_or_invalid_output(raw):
    from backend.app.reasoning import OllamaReasoningProvider

    provider = OllamaReasoningProvider(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=raw))
    )
    with pytest.raises(ReasoningError):
        provider.extract(conversation(), documents())
