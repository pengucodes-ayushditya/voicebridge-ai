"""Configurable structured extraction over transcript evidence."""

import json
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .config import settings
from .schemas import Conversation, Evidence, Observation

PROMPT_VERSION = "semantic-extraction-v3"
SYSTEM_INSTRUCTIONS = (
    (Path(__file__).parent / "prompts" / "semantic_extraction_v3.md")
    .read_text()
    .strip()
)


class ExtractionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "need",
        "goal",
        "question",
        "objection",
        "constraint",
        "budget",
        "timing",
        "context",
        "sentiment",
    ]
    segment_id: str
    quote: str
    description: str
    capability_id: str | None
    information_status: Literal["explicit", "inferred"]
    confidence: float = Field(ge=0, le=1)
    title: str = ""
    category: str = "customer_need"
    constraints: list[str] = []
    acceptance_criteria: list[str] = []
    open_questions: list[str] = []


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExtractionItem]


class ReasoningError(ValueError):
    pass


def response_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": [
                                "need",
                                "goal",
                                "question",
                                "objection",
                                "constraint",
                                "budget",
                                "timing",
                                "context",
                                "sentiment",
                            ],
                        },
                        "segment_id": {"type": "string"},
                        "quote": {"type": "string"},
                        "description": {"type": "string"},
                        "capability_id": {"type": ["string", "null"]},
                        "information_status": {
                            "type": "string",
                            "enum": ["explicit", "inferred"],
                        },
                        "confidence": {"type": "number"},
                        "title": {"type": "string"},
                        "category": {"type": "string"},
                        "constraints": {"type": "array", "items": {"type": "string"}},
                        "acceptance_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "open_questions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "kind",
                        "segment_id",
                        "quote",
                        "description",
                        "capability_id",
                        "information_status",
                        "confidence",
                        "title",
                        "category",
                        "constraints",
                        "acceptance_criteria",
                        "open_questions",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }


class OpenAIReasoningProvider:
    """Uses the official OpenAI Responses API with strict JSON schema output."""

    def __init__(
        self, api_key: str | None = None, model: str | None = None, transport=None
    ):
        self.api_key = settings.llm_api_key if api_key is None else api_key
        self.model = settings.llm_model if model is None else model
        self.base_url = settings.openai_base_url.rstrip("/")
        self.transport = transport

    def extract(
        self, c: Conversation, approved_knowledge: list[dict]
    ) -> ExtractionResult:
        if not self.api_key or not self.model:
            raise ReasoningError(
                "OpenAI reasoning is selected but LLM_API_KEY or LLM_MODEL is missing."
            )
        transcript = [s.model_dump(mode="json") for s in c.segments]
        knowledge = [
            {
                "id": d["id"],
                "title": d["title"],
                "capability_id": d.get("capability_id"),
                "excerpt": d["excerpt"],
            }
            for d in approved_knowledge
            if d.get("status") == "approved"
        ]
        payload = {
            "model": self.model,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": json.dumps(
                {"segments": transcript, "approved_knowledge": knowledge},
                ensure_ascii=False,
            ),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "conversation_extraction",
                    "strict": True,
                    "schema": response_schema(),
                }
            },
        }
        try:
            with httpx.Client(timeout=45, transport=self.transport) as client:
                response = client.post(
                    self.base_url + "/responses",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
            if not response.is_success:
                raise ReasoningError(
                    f"OpenAI Responses API returned HTTP {response.status_code}; verify model access and API credits."
                )
            raw = response.json()
            if raw.get("status") != "completed":
                raise ReasoningError(
                    "Reasoning response was incomplete or refused; no extraction was applied."
                )
            text_parts = []
            for output in raw.get("output", []):
                if output.get("type") == "message":
                    for item in output.get("content", []):
                        if item.get("type") == "refusal":
                            raise ReasoningError(
                                "Reasoning provider refused the extraction; review the transcript manually."
                            )
                        if item.get("type") == "output_text":
                            text_parts.append(item["text"])
            if not text_parts:
                raise ReasoningError("Reasoning provider returned no structured text.")
            result = ExtractionResult.model_validate_json("".join(text_parts))
            if self.transport is None:
                from .verification import record_reasoning_success

                record_reasoning_success()
            return result
        except ReasoningError:
            raise
        except (
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            ValidationError,
        ) as exc:
            raise ReasoningError(
                "Reasoning response was unavailable or did not match the required schema. No extraction was applied."
            ) from exc


class OllamaReasoningProvider:
    """Local Ollama structured extraction with the same evidence contract."""

    def __init__(self, transport=None):
        self.transport = transport

    def extract(
        self, c: Conversation, approved_knowledge: list[dict]
    ) -> ExtractionResult:
        payload = {
            "model": settings.llm_model,
            "think": False,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "segments": [s.model_dump(mode="json") for s in c.segments],
                            "approved_knowledge": [
                                d
                                for d in approved_knowledge
                                if d.get("status") == "approved"
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "format": response_schema(),
            "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 4096},
        }
        try:
            with httpx.Client(timeout=180, transport=self.transport) as client:
                response = client.post(
                    settings.ollama_base_url.rstrip("/") + "/api/chat", json=payload
                )
            if not response.is_success:
                raise ReasoningError(
                    f"Local Ollama returned HTTP {response.status_code}; check that the model is installed."
                )
            raw = response.json()
            if not raw.get("done") or raw.get("done_reason") == "length":
                raise ReasoningError(
                    "Local extraction was incomplete; no extraction was applied."
                )
            result = ExtractionResult.model_validate_json(raw["message"]["content"])
            if self.transport is None:
                from .verification import record_reasoning_success

                record_reasoning_success()
            return result
        except ReasoningError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ReasoningError(
                "Local Ollama is unavailable or returned invalid structured output."
            ) from exc


def apply_extraction(
    c: Conversation, result: ExtractionResult, knowledge: list[dict]
) -> None:
    """Accept only exact customer evidence and catalogue IDs from the model."""
    segments = {s.id: s for s in c.segments}
    docs = {
        d.get("capability_id"): d
        for d in knowledge
        if d.get("capability_id") and d.get("status") == "approved"
    }
    grouped: dict[str, list[tuple[ExtractionItem, Evidence]]] = {}
    observations = []
    unknown_needs = []
    for index, item in enumerate(result.items):
        segment = segments.get(item.segment_id)
        if (
            segment is None
            or segment.role != "customer"
            or not item.quote.strip()
            or item.quote not in segment.text
        ):
            continue
        ev = Evidence(
            segment_id=segment.id,
            quote=item.quote,
            speaker_role="customer",
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
        )
        if item.capability_id in docs:
            candidate = (
                item
                if item.kind == "need"
                else item.model_copy(update={"information_status": "inferred"})
            )
            grouped.setdefault(item.capability_id, []).append((candidate, ev))
            if item.kind != "need":
                observations.append(
                    Observation(
                        id=f"obs-model-{index}-{segment.id}",
                        kind=item.kind,
                        description=item.description,
                        evidence=[ev],
                        information_status=item.information_status,
                        confidence=item.confidence,
                    )
                )
        elif item.kind == "need":
            unknown_needs.append((index, item, ev))
        else:
            observations.append(
                Observation(
                    id=f"obs-model-{index}-{segment.id}",
                    kind=item.kind,
                    description=item.description,
                    evidence=[ev],
                    information_status=item.information_status,
                    confidence=item.confidence,
                )
            )
    c.observations = observations
    c.requirements = []
    # Requirements with a supported catalogue mapping use that document's criteria and status downstream.
    from .schemas import Requirement

    for index, item, ev in unknown_needs:
        criteria = item.acceptance_criteria or [
            "Confirm intended behaviour and testable criteria with the customer before approval."
        ]
        c.requirements.append(
            Requirement(
                id=f"req-custom-{index}-{ev.segment_id}",
                title=item.title or "Review customer need",
                description=item.description,
                original_description=item.description,
                category=item.category,
                information_status=item.information_status,
                confidence=item.confidence,
                user_story="As a customer, I want " + item.description,
                acceptance_criteria=criteria,
                original_acceptance_criteria=criteria,
                constraints=[
                    value for value in item.constraints if value and value in ev.quote
                ],
                open_questions=item.open_questions
                or ["What exact behaviour and acceptance checks should be confirmed?"],
                evidence=[ev],
            )
        )
    for cap, entries in grouped.items():
        doc = docs[cap]
        evidence = list({ev.segment_id: ev for _, ev in entries}.values())
        description = "; ".join(dict.fromkeys(item.description for item, _ in entries))
        status = (
            "explicit"
            if any(item.information_status == "explicit" for item, _ in entries)
            else "inferred"
        )
        c.requirements.append(
            Requirement(
                id="req-" + cap,
                capability_id=cap,
                title=doc["requirement"],
                description=description,
                original_description=description,
                category=doc["category"],
                priority="P0" if cap == "privacy" else "P1",
                information_status=status,
                confidence=min(item.confidence for item, _ in entries),
                user_story="As a customer, I want " + description,
                acceptance_criteria=list(
                    dict.fromkeys(
                        doc["criteria"]
                        + [
                            criterion
                            for item, _ in entries
                            for criterion in item.acceptance_criteria
                        ]
                    )
                ),
                original_acceptance_criteria=list(
                    dict.fromkeys(
                        doc["criteria"]
                        + [
                            criterion
                            for item, _ in entries
                            for criterion in item.acceptance_criteria
                        ]
                    )
                ),
                constraints=list(
                    dict.fromkeys(
                        ([doc["excerpt"]] if cap == "privacy" else [])
                        + [
                            value
                            for item, ev in entries
                            for value in item.constraints
                            if value and value in ev.quote
                        ]
                    )
                ),
                dependencies=doc["dependencies"],
                open_questions=list(
                    dict.fromkeys(
                        doc["questions"]
                        + [
                            question
                            for item, _ in entries
                            for question in item.open_questions
                        ]
                    )
                ),
                evidence=evidence,
            )
        )
    covered = {e.segment_id for r in c.requirements for e in r.evidence}
    covered.update(
        ev.segment_id
        for observation in observations
        if observation.kind in {"sentiment", "context"}
        for ev in observation.evidence
    )
    for segment in [
        s for s in c.segments if s.role == "customer" and s.id not in covered
    ]:
        quote = segment.text
        c.requirements.append(
            Requirement(
                id="req-review-" + segment.id,
                title="Review extracted customer statement",
                description=quote,
                original_description=quote,
                category="needs_review",
                information_status="inferred",
                confidence=0.2,
                user_story="Confirm the customer's intended behaviour.",
                acceptance_criteria=[
                    "Confirm intended behaviour and testable criteria before approval."
                ],
                evidence=[
                    Evidence(
                        segment_id=segment.id,
                        quote=quote,
                        speaker_role="customer",
                        start_ms=segment.start_ms,
                        end_ms=segment.end_ms,
                    )
                ],
                open_questions=["What exact behaviour is requested?"],
            )
        )


def structured_completion(
    name: str, schema: dict, instructions: str, data: dict
) -> dict:
    """Bounded structured tasks; callers validate source references before applying."""
    content = json.dumps(data, ensure_ascii=False)
    try:
        with httpx.Client(
            timeout=180 if settings.llm_provider == "ollama" else 60
        ) as client:
            if settings.llm_provider == "ollama":
                response = client.post(
                    settings.ollama_base_url.rstrip("/") + "/api/chat",
                    json={
                        "model": settings.llm_model,
                        "messages": [
                            {"role": "system", "content": instructions},
                            {"role": "user", "content": content},
                        ],
                        "format": schema,
                        "stream": False,
                        "think": False,
                        "options": {
                            "temperature": 0,
                            "num_ctx": 16384,
                            "num_predict": 4096,
                        },
                    },
                )
                if not response.is_success:
                    raise ReasoningError(
                        f"Local model returned HTTP {response.status_code}."
                    )
                raw = response.json()
                if not raw.get("done") or raw.get("done_reason") == "length":
                    raise ReasoningError(
                        "Local model output was incomplete; no result was applied."
                    )
                return json.loads(raw["message"]["content"])
            if (
                settings.llm_provider == "openai"
                and settings.llm_api_key
                and settings.llm_model
            ):
                response = client.post(
                    settings.openai_base_url.rstrip("/") + "/responses",
                    headers={"Authorization": "Bearer " + settings.llm_api_key},
                    json={
                        "model": settings.llm_model,
                        "instructions": instructions,
                        "input": content,
                        "text": {
                            "format": {
                                "type": "json_schema",
                                "name": name,
                                "strict": True,
                                "schema": schema,
                            }
                        },
                    },
                )
                if not response.is_success:
                    raise ReasoningError(
                        f"Reasoning model returned HTTP {response.status_code}."
                    )
                raw = response.json()
                if raw.get("status") != "completed":
                    raise ReasoningError(
                        "Model output was incomplete; no result was applied."
                    )
                parts = [
                    part["text"]
                    for output in raw.get("output", [])
                    if output.get("type") == "message"
                    for part in output.get("content", [])
                    if part.get("type") == "output_text"
                ]
                return json.loads("".join(parts))
            raise ReasoningError("Configure a reasoning model to use this operation.")
    except ReasoningError:
        raise
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise ReasoningError(
            "The reasoning model was unavailable or returned invalid structured output."
        ) from exc


def add_catalogue_coverage_candidates(c: Conversation, knowledge: list[dict]) -> None:
    """Surface known-topic omissions as inferred review items, never confirmed needs."""
    from .knowledge import matches
    from .schemas import Requirement

    mapped = {r.capability_id for r in c.requirements}
    for doc in knowledge:
        cap = doc.get("capability_id")
        if not cap or cap in mapped or doc.get("status") != "approved":
            continue
        hits = [s for s in c.segments if s.role == "customer" and matches(s.text, doc)]
        if not hits:
            continue
        description = (
            "Catalogue coverage candidate: "
            + doc["description"]
            + " Customer context: "
            + " ".join(s.text for s in hits)
        )
        c.requirements.append(
            Requirement(
                id="req-coverage-" + cap,
                capability_id=cap,
                title=doc["requirement"],
                description=description,
                original_description=description,
                category=doc["category"],
                information_status="inferred",
                confidence=0.35,
                user_story="Validate whether this documented capability matches the customer statement.",
                acceptance_criteria=doc["criteria"],
                original_acceptance_criteria=doc["criteria"],
                dependencies=doc["dependencies"],
                open_questions=[
                    "The model did not map this topic. Confirm the intended requirement with the customer."
                ]
                + doc["questions"],
                evidence=[
                    Evidence(
                        segment_id=s.id,
                        quote=s.text,
                        speaker_role=s.role,
                        start_ms=s.start_ms,
                        end_ms=s.end_ms,
                    )
                    for s in hits
                ],
                extraction_origin="catalogue_coverage",
            )
        )
