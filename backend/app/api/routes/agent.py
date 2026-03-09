from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.agent.schemas import (
    CapabilityContextResponse,
    CapabilityDefinition,
    CapabilityExecutionRequest,
    CapabilityExecutionResult,
)
from app.agent.service import AgentCapabilityService
from app.core.auth import get_current_user, require_any_role
from app.core.database import get_session

router = APIRouter()


@router.get("/capabilities", response_model=list[CapabilityDefinition])
def list_capabilities(
    _: None = Depends(require_any_role("trader", "risk_manager", "auditor")),
) -> list[CapabilityDefinition]:
    return AgentCapabilityService.list_capabilities()


@router.get("/capabilities/{capability_name}/context", response_model=CapabilityContextResponse)
def get_capability_context(
    capability_name: str,
    entity_id: UUID | None = Query(None),
    _: None = Depends(require_any_role("trader", "risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> CapabilityContextResponse:
    return AgentCapabilityService.get_context(
        session,
        capability_name,
        entity_id=entity_id,
    )


@router.post("/execute", response_model=CapabilityExecutionResult)
def execute_capability(
    payload: CapabilityExecutionRequest,
    _: None = Depends(require_any_role("trader", "risk_manager", "auditor")),
    session: Session = Depends(get_session),
    user: dict[str, Any] = Depends(get_current_user),
) -> CapabilityExecutionResult:
    return AgentCapabilityService.execute(session, payload, user=user)
