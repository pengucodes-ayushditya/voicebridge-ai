"""Version-one source drafts and explicit technical review for the local prototype."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import JSON, Column, String

from .schemas import Domain
from .store import Base, Session, engine, lock


class KnowledgeRecord(Base):
    __tablename__ = "knowledge_sources"
    id = Column(String, primary_key=True)
    payload = Column(JSON, nullable=False)


Base.metadata.create_all(engine)


class NewSource(BaseModel):
    domain_id: Domain = "synthetic-device-lifecycle"
    title: str = Field(min_length=3, max_length=150)
    excerpt: str = Field(min_length=20, max_length=10000)
    category: str = Field(default="product_documentation", max_length=80)
    keywords: list[str] = Field(min_length=1, max_length=30)
    capability_id: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{1,49}$")
    status_value: Literal["supported", "conditional", "unsupported", "unknown"] = (
        "unknown"
    )
    criteria: list[str] = []
    dependencies: list[str] = []
    questions: list[str] = []
    synthetic_consent: Literal[True]

    @model_validator(mode="after")
    def complete_capability(self):
        if self.capability_id and not self.criteria:
            raise ValueError(
                "A capability needs proposed testable acceptance criteria."
            )
        if self.status_value == "conditional" and not self.dependencies:
            raise ValueError("Conditional support needs explicit dependencies.")
        if any(
            not value.strip() or len(value) > 2000
            for values in [
                self.keywords,
                self.criteria,
                self.dependencies,
                self.questions,
            ]
            for value in values
        ):
            raise ValueError("List entries must contain 1–2000 characters.")
        return self


class SourceApproval(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


def all_sources():
    with Session() as db:
        return [r.payload for r in db.query(KnowledgeRecord).all()]


def create(body):
    doc = body.model_dump(exclude={"synthetic_consent"})
    doc.update(
        id="kb-custom-" + uuid4().hex[:10],
        status="draft",
        version="1",
        owner="Technical Reviewer",
        requirement=body.title,
        description=body.excerpt,
        created_at=datetime.now(UTC).isoformat(),
    )
    with Session.begin() as db:
        db.add(KnowledgeRecord(id=doc["id"], payload=doc))
    return doc


def approve(sid, reason):
    from .knowledge import documents
    from .reviews import ReviewError

    with lock, Session.begin() as db:
        record = db.get(KnowledgeRecord, sid)
        if not record:
            raise ReviewError("Source draft not found.")
        doc = dict(record.payload)
        if doc["status"] != "draft":
            raise ReviewError("This source has already been reviewed.")
        if doc.get("capability_id") and any(
            d.get("capability_id") == doc["capability_id"] for d in documents()
        ):
            raise ReviewError(
                "This capability already has an approved source. Use a new capability ID or omit the ID for supplementary documentation."
            )
        doc.update(
            status="approved",
            review_reason=reason,
            approved_at=datetime.now(UTC).isoformat(),
        )
        record.payload = doc
    return doc
