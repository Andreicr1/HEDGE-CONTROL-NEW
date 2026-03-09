from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CapabilityMutability(str, Enum):
    read = "read"
    write = "write"


class ExecutionStatus(str, Enum):
    completed = "completed"
    review_required = "review_required"
    failed = "failed"


class CapabilityDefinition(BaseModel):
    name: str = Field(..., max_length=128)
    domain: str = Field(..., max_length=64)
    description: str = Field(..., max_length=500)
    mutability: CapabilityMutability
    auth_scopes: list[str] = Field(default_factory=list)
    idempotent: bool = False
    context_entity_type: str | None = Field(None, max_length=64)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class CapabilityExecutionRequest(BaseModel):
    capability: str = Field(..., max_length=128)
    input: dict[str, Any] = Field(default_factory=dict)
    context_entity_id: UUID | None = None
    correlation_id: str | None = Field(None, max_length=128)
    actor_type: str = Field("agent", max_length=32)
    actor_id: str | None = Field(None, max_length=128)


class ExecutionEntityRef(BaseModel):
    entity_type: str = Field(..., max_length=64)
    entity_id: UUID
    label: str | None = Field(None, max_length=128)


class UIVisibilityHint(BaseModel):
    channel: str = Field("polling", max_length=32)
    resource_paths: list[str] = Field(default_factory=list)
    message: str | None = Field(None, max_length=500)


class AgentActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    capability_name: str = Field(..., max_length=128)
    status: ExecutionStatus
    summary: str = Field(..., max_length=500)
    actor_type: str = Field(..., max_length=32)
    actor_id: str | None = Field(None, max_length=128)
    execution_id: UUID
    correlation_id: str | None = Field(None, max_length=128)
    timestamp_utc: str = Field(..., max_length=64)


class CapabilityContextResponse(BaseModel):
    capability: CapabilityDefinition
    context: dict[str, Any] = Field(default_factory=dict)
    latest_activity: AgentActivityRead | None = None


class CapabilityExecutionResult(BaseModel):
    execution_id: UUID
    capability: str = Field(..., max_length=128)
    status: ExecutionStatus
    mutability: CapabilityMutability
    summary: str = Field(..., max_length=500)
    review_reason: str | None = Field(None, max_length=500)
    audit_event_id: UUID | None = None
    entity_refs: list[ExecutionEntityRef] = Field(default_factory=list)
    ui_visibility: UIVisibilityHint | None = None
    result: Any = None
