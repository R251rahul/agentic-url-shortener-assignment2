from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SAFE_STOPPED = "SAFE_STOPPED"
    ROLLED_BACK = "ROLLED_BACK"

class NodeStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    ROLLED_BACK = "ROLLED_BACK"

class UrlCreate(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    custom_alias: str | None = Field(default=None, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    expires_at: datetime | None = None

class UrlResponse(BaseModel):
    code: str
    short_url: str
    target_url: str
    expires_at: datetime | None

class AnalyticsResponse(BaseModel):
    code: str
    target_url: str
    clicks: int
    last_accessed_at: datetime | None

class ScenarioRequest(BaseModel):
    scenario: str = Field(pattern=r"^(greenfield|brownfield|ambiguous)$")
    requirement: str = Field(min_length=10)
    auto_approve_low_risk: bool = True

class ApprovalRequest(BaseModel):
    approved: bool
    comment: str = ""

class AuditEvent(BaseModel):
    timestamp: datetime = Field(default_factory=utcnow)
    run_id: str
    node_id: str | None = None
    event: str
    actor: str
    details: dict[str, Any] = Field(default_factory=dict)
