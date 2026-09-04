from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


EntityType = Literal[
    "person",
    "protected_person",
    "organization",
    "location",
    "account",
    "phone",
    "event",
    "vehicle",
    "crime",
]
Severity = Literal["critical", "high", "medium", "low"]


class GraphNode(BaseModel):
    id: str
    name: str
    type: EntityType
    risk: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    community: int
    description: str | None = None
    location: str | None = None
    lastSeen: str | None = None
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    confidence: int = Field(ge=0, le=100)
    anomalous: bool = False
    evidence_record_ids: list[str] = Field(default_factory=list)
    evidence_hashes: list[str] = Field(default_factory=list)
    source_types: list[str] = Field(default_factory=list)
    observed_at: str | None = None
    epistemic_status: Literal["observed", "derived"] = "observed"


class GraphPayload(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class UploadRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    filename: str
    size: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "uploaded"
    records: int = 0


class PipelineRequest(BaseModel):
    upload_id: str
    activate: bool = True


class PipelineStage(BaseModel):
    id: str
    name: str
    progress: int = 0
    status: Literal["queued", "running", "complete", "failed"] = "queued"


class PipelineState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    upload_id: str
    requested_by: str = "local-analyst"
    activate: bool = True
    status: str = "queued"
    progress: int = 0
    stages: list[PipelineStage]
    logs: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Alert(BaseModel):
    id: str
    title: str
    detail: str
    severity: Severity
    time: str
    entityId: str
    acknowledged: bool = False
    confidence: int


class SearchRequest(BaseModel):
    query: str = ""
    entity_types: list[EntityType] = Field(default_factory=list)
    min_risk: int = 0
    limit: int = Field(default=25, ge=1, le=250)


class ConfigUpdate(BaseModel):
    theme: str | None = None
    default_layout: str | None = None
    alert_sensitivity: int | None = Field(default=None, ge=0, le=100)
    nlp_model: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class LoginRequest(BaseModel):
    email: str
    password: str


class ResolutionDecisionRequest(BaseModel):
    decision: Literal["keep-separate", "escalate"]
    rationale: str = Field(min_length=3, max_length=500)


class ProtectedRevealRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)
    authorization_reference: str = Field(min_length=3, max_length=120)
