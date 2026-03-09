from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.schemas import AgentActivityRead, ExecutionStatus
from app.models.audit import AuditEvent
from app.services.audit_trail_service import AuditTrailService, normalize_payload_raw


def record_agent_execution(
    session: Session,
    *,
    capability_name: str,
    target_entity_type: str,
    target_entity_id: uuid.UUID,
    execution_id: uuid.UUID,
    correlation_id: str | None,
    actor_type: str,
    actor_id: str | None,
    status: ExecutionStatus,
    summary: str,
    input_payload: object,
    result_payload: object,
) -> AuditEvent:
    payload = {
        "actor_id": actor_id,
        "actor_type": actor_type,
        "capability_name": capability_name,
        "correlation_id": correlation_id,
        "execution_id": str(execution_id),
        "input": input_payload,
        "result": result_payload,
        "status": status.value,
        "summary": summary,
    }
    payload_raw, payload_obj = normalize_payload_raw(payload)
    return AuditTrailService.record(
        session,
        event_id=uuid.uuid4(),
        entity_type=target_entity_type,
        entity_id=target_entity_id,
        event_type="agent_execution",
        payload_raw=payload_raw,
        payload_obj=payload_obj,
    )


def get_latest_agent_activity(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
) -> AgentActivityRead | None:
    event = (
        session.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == entity_type,
            AuditEvent.entity_id == entity_id,
            AuditEvent.event_type == "agent_execution",
        )
        .order_by(AuditEvent.timestamp_utc.desc(), AuditEvent.id.desc())
        .first()
    )
    if event is None or not isinstance(event.payload, dict):
        return None

    payload = event.payload
    timestamp = event.timestamp_utc
    timestamp_utc = (
        timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)
    )
    return AgentActivityRead(
        capability_name=str(payload.get("capability_name") or "unknown"),
        status=ExecutionStatus(str(payload.get("status") or ExecutionStatus.completed.value)),
        summary=str(payload.get("summary") or "Automated action executed"),
        actor_type=str(payload.get("actor_type") or "agent"),
        actor_id=payload.get("actor_id"),
        execution_id=uuid.UUID(str(payload.get("execution_id"))),
        correlation_id=payload.get("correlation_id"),
        timestamp_utc=timestamp_utc,
    )
