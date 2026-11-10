from typing import Literal

from pydantic import BaseModel, Field, model_validator

Role = Literal["customer", "sales", "unknown"]
Domain = Literal["synthetic-device-lifecycle", "marketplace"]
Feasibility = Literal["supported", "conditional", "unsupported", "unknown"]


class Segment(BaseModel):
    id: str
    speaker_id: str
    role: Role = "unknown"
    text: str = Field(min_length=1, max_length=10000)
    original_text: str = ""
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    language: str | None = None
    parent_segment_id: str | None = None

    @model_validator(mode="after")
    def valid_times(self):
        if (
            self.start_ms is not None
            and self.end_ms is not None
            and self.end_ms < self.start_ms
        ):
            raise ValueError("Segment end precedes start")
        return self


class Evidence(BaseModel):
    segment_id: str
    quote: str
    speaker_role: Role
    start_ms: int | None = None
    end_ms: int | None = None


class Observation(BaseModel):
    id: str
    kind: str
    description: str
    evidence: list[Evidence]
    information_status: Literal["explicit", "inferred"] = "inferred"
    confidence: float = Field(default=0.5, ge=0, le=1)
    dismissed: bool = False


class Requirement(BaseModel):
    extraction_origin: str = "rules"
    id: str
    capability_id: str | None = None
    superseded_by: list[str] = []
    supersedes: list[str] = []
    title: str
    description: str
    original_description: str
    category: str
    priority: Literal["P0", "P1", "P2"] = "P1"
    information_status: Literal["explicit", "inferred", "assumption"] = "explicit"
    confidence: float = Field(ge=0, le=1)
    constraints: list[str] = []
    dependencies: list[str] = []
    acceptance_criteria: list[str] = []
    original_acceptance_criteria: list[str] = []
    user_story: str
    evidence: list[Evidence]
    open_questions: list[str] = []
    pm_status: Literal[
        "pending", "accepted", "needs_clarification", "deferred", "rejected"
    ] = "pending"
    notes: str = ""

    @model_validator(mode="after")
    def traceable(self):
        if not self.evidence and self.information_status != "assumption":
            raise ValueError("Non-assumptions require evidence")
        return self


class Assessment(BaseModel):
    support_bound: Feasibility | None = None
    grounding_note: str = ""
    requirement_id: str
    status: Feasibility
    explanation: str
    documentation_sources: list[str]
    dependencies: list[str] = []
    risks: list[str] = []
    clarification_questions: list[str] = []
    reviewer_status: Literal["pending", "approved", "rejected"] = "pending"
    notes: str = ""


class Finding(BaseModel):
    target_id: str | None = None
    origin: str = "rules"
    id: str
    finding_type: str
    severity: Literal["high", "medium", "low"]
    description: str
    original_evidence: list[Evidence]
    downstream_text: str
    suggested_correction: str
    reviewer_status: Literal["open", "acknowledged", "resolved", "dismissed"] = "open"
    reviewer_notes: str = ""


class CustomerResponse(BaseModel):
    generation_provider: str = "approved-catalogue-templates"
    text: str
    language: Literal["English", "Hinglish", "Hindi"]
    approved: bool = False
    sources: list[str]
    audio_path: str | None = None


class Conversation(BaseModel):
    id: str
    title: str
    domain_id: Domain = "synthetic-device-lifecycle"
    synthetic: bool = True
    source: str
    version: int = 1
    status: str = "ready"
    error: str | None = None
    transcription_mode: Literal["batch", "rest"] = "batch"
    provider_job_id: str | None = None
    audio_path: str | None = None
    transcription_model: str = "Manual transcript"
    segments: list[Segment] = []
    original_segments: list[Segment] = []
    requirements: list[Requirement] = []
    observations: list[Observation] = []
    assessments: list[Assessment] = []
    findings: list[Finding] = []
    sales: dict = {}
    signals: list[dict] = []
    response: CustomerResponse | None = None
    audit_log: list[dict] = []
    node_runs: list[dict] = []
    semantic_audit: dict | None = None
    processing_step: str | None = None
    copilot_history: list[dict] = []
    transcript_lineage: list[dict] = []


class CreateTranscript(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    segments: list[Segment] = Field(min_length=1, max_length=300)
    synthetic_consent: Literal[True]
    domain_id: Domain = "synthetic-device-lifecycle"


class ReviewRequest(BaseModel):
    version: int
    action: Literal[
        "pm",
        "sales",
        "engineering",
        "finding",
        "response",
        "draft",
        "audit",
        "analyse",
        "merge",
        "split",
        "observation",
        "semantic_audit",
    ]
    item_id: str | None = None
    changes: dict = {}
    reason: str = Field(default="", max_length=2000)


class TranscriptEdit(BaseModel):
    version: int
    segments: list[Segment] = Field(min_length=1, max_length=300)
    reason: str = Field(min_length=1, max_length=1000)
