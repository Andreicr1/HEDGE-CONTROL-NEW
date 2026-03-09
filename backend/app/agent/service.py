from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.audit import get_latest_agent_activity, record_agent_execution
from app.agent.context import build_rfq_context, build_rfq_read_model
from app.agent.registry import (
    CapabilityRegistration,
    get_capability,
    has_capability,
    iter_capabilities,
    register_capability,
)
from app.agent.schemas import (
    CapabilityContextResponse,
    CapabilityDefinition,
    CapabilityExecutionRequest,
    CapabilityExecutionResult,
    CapabilityMutability,
    ExecutionEntityRef,
    ExecutionStatus,
    UIVisibilityHint,
)
from app.schemas.audit import AuditEventRead
from app.schemas.market_data import CashSettlementPriceRead
from app.schemas.rfq import (
    RFQAwardRequest,
    RFQCreate,
    RFQQuoteCreate,
    RFQRefreshRequest,
    RFQRejectRequest,
)
from app.schemas.whatsapp import WhatsAppInboundMessage
from app.services.audit_trail_service import AuditTrailService
from app.services.cash_settlement_prices import list_cash_settlement_prices
from app.services.contract_service import ContractService
from app.services.exposure_engine import ExposureEngineService
from app.services.order_service import OrderService
from app.services.rfq_orchestrator import RFQOrchestrator
from app.services.rfq_service import RFQService


class RfqIdInput(BaseModel):
    rfq_id: UUID


class OrderListToolInput(BaseModel):
    order_type: str | None = None
    price_type: str | None = None
    include_deleted: bool = False
    cursor: str | None = None
    limit: int = Field(50, ge=1, le=200)


class ContractListToolInput(BaseModel):
    status: str | None = None
    classification: str | None = None
    commodity: str | None = None
    include_deleted: bool = False
    cursor: str | None = None
    limit: int = Field(50, ge=1, le=200)


class ExposureNetToolInput(BaseModel):
    commodity: str | None = None


class AuditEventListToolInput(BaseModel):
    entity_type: str | None = None
    entity_id: UUID | None = None
    start: datetime | None = None
    end: datetime | None = None
    cursor: str | None = None
    limit: int = Field(50, ge=1, le=200)


class MarketDataCashSettlementListInput(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    symbol: str | None = None
    limit: int = Field(500, ge=1, le=5000)


class InboundMessageToolInput(BaseModel):
    from_phone: str = Field(..., max_length=50)
    text: str = Field(..., max_length=4000)
    sender_name: str | None = Field(None, max_length=200)
    message_id: str | None = Field(None, max_length=128)
    timestamp: datetime | None = None


def _ui_hint_for_rfq(rfq_id: UUID, message: str) -> UIVisibilityHint:
    encoded = str(rfq_id)
    return UIVisibilityHint(
        channel="polling",
        message=message,
        resource_paths=[
            f"/rfqs/{encoded}",
            f"/rfqs/{encoded}/quotes",
            f"/rfqs/{encoded}/state-events",
        ],
    )


def _entity_ref(entity_type: str, entity_id: UUID, label: str | None = None) -> ExecutionEntityRef:
    return ExecutionEntityRef(entity_type=entity_type, entity_id=entity_id, label=label)


def _actor_id(user: dict[str, Any], request: CapabilityExecutionRequest) -> str | None:
    return request.actor_id or user.get("sub") or user.get("name")


def _ensure_roles(user: dict[str, Any], required_roles: list[str]) -> None:
    if not required_roles:
        return
    user_roles = set(user.get("roles") or [])
    if not user_roles.intersection(required_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _record_mutation(
    session: Session,
    *,
    execution_id: UUID,
    request: CapabilityExecutionRequest,
    capability_name: str,
    target_entity_type: str,
    target_entity_id: UUID,
    summary: str,
    result_payload: object,
) -> UUID:
    audit_event = record_agent_execution(
        session,
        capability_name=capability_name,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        execution_id=execution_id,
        correlation_id=request.correlation_id,
        actor_type=request.actor_type,
        actor_id=request.actor_id,
        status=ExecutionStatus.completed,
        summary=summary,
        input_payload=request.input,
        result_payload=result_payload,
    )
    return audit_event.id


def _result_payload(result: object) -> object:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    return result


def _execute_rfq_get(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = RfqIdInput.model_validate(request.input)
    rfq = build_rfq_read_model(session, payload.rfq_id)
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="rfq.get",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.read,
        summary=f"Loaded RFQ {rfq.rfq_number}",
        entity_refs=[_entity_ref("rfq", rfq.id, rfq.rfq_number)],
        ui_visibility=_ui_hint_for_rfq(rfq.id, f"RFQ {rfq.rfq_number} loaded for automation context"),
        result=rfq.model_dump(mode="json"),
    )


def _execute_rfq_create(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = RFQCreate.model_validate(request.input)
    rfq = RFQService.create(session, payload)
    session.commit()
    session.refresh(rfq)
    rfq_read = build_rfq_read_model(session, rfq.id)
    summary = f"Created RFQ {rfq_read.rfq_number} via agent capability"
    audit_event_id = _record_mutation(
        session,
        execution_id=execution_id,
        request=request,
        capability_name="rfq.create",
        target_entity_type="rfq",
        target_entity_id=rfq.id,
        summary=summary,
        result_payload=rfq_read.model_dump(mode="json"),
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="rfq.create",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.write,
        summary=summary,
        audit_event_id=audit_event_id,
        entity_refs=[_entity_ref("rfq", rfq.id, rfq_read.rfq_number)],
        ui_visibility=_ui_hint_for_rfq(rfq.id, summary),
        result=rfq_read.model_dump(mode="json"),
    )


def _execute_rfq_add_quote(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = RFQQuoteCreate.model_validate(request.input)
    quote = RFQService.submit_quote(session, payload.rfq_id, payload)
    session.commit()
    session.refresh(quote)
    summary = f"Added quote for RFQ {payload.rfq_id}"
    audit_event_id = _record_mutation(
        session,
        execution_id=execution_id,
        request=request,
        capability_name="rfq.add_quote",
        target_entity_type="rfq",
        target_entity_id=payload.rfq_id,
        summary=summary,
        result_payload={"quote_id": str(quote.id)},
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="rfq.add_quote",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.write,
        summary=summary,
        audit_event_id=audit_event_id,
        entity_refs=[
            _entity_ref("rfq", payload.rfq_id),
            _entity_ref("rfq_quote", quote.id),
        ],
        ui_visibility=_ui_hint_for_rfq(payload.rfq_id, summary),
        result={"quote_id": str(quote.id)},
    )


def _execute_rfq_refresh(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = RFQRefreshRequest.model_validate(request.input)
    rfq = RFQService.refresh(session, payload.rfq_id, payload.user_id)
    session.commit()
    rfq_read = build_rfq_read_model(session, payload.rfq_id)
    summary = f"Refreshed RFQ {rfq.rfq_number} invitations via agent capability"
    audit_event_id = _record_mutation(
        session,
        execution_id=execution_id,
        request=request,
        capability_name="rfq.refresh",
        target_entity_type="rfq",
        target_entity_id=payload.rfq_id,
        summary=summary,
        result_payload=rfq_read.model_dump(mode="json"),
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="rfq.refresh",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.write,
        summary=summary,
        audit_event_id=audit_event_id,
        entity_refs=[_entity_ref("rfq", payload.rfq_id, rfq.rfq_number)],
        ui_visibility=_ui_hint_for_rfq(payload.rfq_id, summary),
        result=rfq_read.model_dump(mode="json"),
    )


def _execute_rfq_reject(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = RFQRejectRequest.model_validate(request.input)
    rfq = RFQService.reject(session, payload.rfq_id, payload.user_id)
    session.commit()
    rfq_read = build_rfq_read_model(session, payload.rfq_id)
    summary = f"Rejected RFQ {rfq.rfq_number} via agent capability"
    audit_event_id = _record_mutation(
        session,
        execution_id=execution_id,
        request=request,
        capability_name="rfq.reject",
        target_entity_type="rfq",
        target_entity_id=payload.rfq_id,
        summary=summary,
        result_payload=rfq_read.model_dump(mode="json"),
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="rfq.reject",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.write,
        summary=summary,
        audit_event_id=audit_event_id,
        entity_refs=[_entity_ref("rfq", payload.rfq_id, rfq.rfq_number)],
        ui_visibility=_ui_hint_for_rfq(payload.rfq_id, summary),
        result=rfq_read.model_dump(mode="json"),
    )


def _execute_rfq_award(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = RFQAwardRequest.model_validate(request.input)
    rfq = RFQService.award(session, payload.rfq_id, payload.user_id)
    session.commit()
    rfq_read = build_rfq_read_model(session, payload.rfq_id)
    summary = f"Awarded RFQ {rfq.rfq_number} via agent capability"
    audit_event_id = _record_mutation(
        session,
        execution_id=execution_id,
        request=request,
        capability_name="rfq.award",
        target_entity_type="rfq",
        target_entity_id=payload.rfq_id,
        summary=summary,
        result_payload=rfq_read.model_dump(mode="json"),
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="rfq.award",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.write,
        summary=summary,
        audit_event_id=audit_event_id,
        entity_refs=[_entity_ref("rfq", payload.rfq_id, rfq.rfq_number)],
        ui_visibility=_ui_hint_for_rfq(payload.rfq_id, summary),
        result=rfq_read.model_dump(mode="json"),
    )


def _execute_rfq_process_inbound(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = InboundMessageToolInput.model_validate(request.input)
    message = WhatsAppInboundMessage(
        message_id=payload.message_id or f"agent.{uuid.uuid4().hex[:12]}",
        from_phone=payload.from_phone,
        timestamp=payload.timestamp or datetime.now(UTC),
        text=payload.text,
        sender_name=payload.sender_name,
    )
    result = RFQOrchestrator._process_single_message(session, message)
    status_map = {
        "needs_human_review": ExecutionStatus.review_required,
        "counterparty_question": ExecutionStatus.review_required,
        "llm_unavailable": ExecutionStatus.failed,
        "auto_quote_failed": ExecutionStatus.failed,
    }
    execution_status = status_map.get(result.get("status", ""), ExecutionStatus.completed)
    rfq_id = result.get("rfq_id")
    entity_refs: list[ExecutionEntityRef] = []
    ui_visibility = None
    audit_event_id = None
    summary = f"Processed inbound RFQ message with outcome {result.get('status', 'unknown')}"
    if rfq_id:
        rfq_uuid = UUID(str(rfq_id))
        entity_refs.append(_entity_ref("rfq", rfq_uuid))
        ui_visibility = _ui_hint_for_rfq(rfq_uuid, summary)
        if execution_status != ExecutionStatus.failed:
            audit_event = record_agent_execution(
                session,
                capability_name="rfq.process_inbound_message",
                target_entity_type="rfq",
                target_entity_id=rfq_uuid,
                execution_id=execution_id,
                correlation_id=request.correlation_id,
                actor_type=request.actor_type,
                actor_id=request.actor_id,
                status=execution_status,
                summary=summary,
                input_payload=request.input,
                result_payload=result,
            )
            audit_event_id = audit_event.id
    if result.get("quote_id"):
        entity_refs.append(_entity_ref("rfq_quote", UUID(str(result["quote_id"]))))

    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="rfq.process_inbound_message",
        status=execution_status,
        mutability=CapabilityMutability.write,
        summary=summary,
        review_reason=result.get("status") if execution_status == ExecutionStatus.review_required else None,
        audit_event_id=audit_event_id,
        entity_refs=entity_refs,
        ui_visibility=ui_visibility,
        result=result,
    )


def _execute_orders_list(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = OrderListToolInput.model_validate(request.input)
    orders = OrderService.list_orders(
        session,
        order_type=payload.order_type,
        price_type=payload.price_type,
        include_deleted=payload.include_deleted,
        cursor=payload.cursor,
        limit=payload.limit,
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="orders.list",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.read,
        summary=f"Loaded {len(orders.items)} orders",
        result=orders.model_dump(mode="json"),
    )


def _execute_contracts_list(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = ContractListToolInput.model_validate(request.input)
    contracts = ContractService.list(
        session,
        status_filter=payload.status,
        classification=payload.classification,
        commodity=payload.commodity,
        include_deleted=payload.include_deleted,
        cursor=payload.cursor,
        limit=payload.limit,
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="contracts.list",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.read,
        summary=f"Loaded {len(contracts.items)} contracts",
        result=contracts.model_dump(mode="json"),
    )


def _execute_exposures_net(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = ExposureNetToolInput.model_validate(request.input)
    items = ExposureEngineService.compute_net_exposure(session, payload.commodity)
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="exposures.net",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.read,
        summary=f"Loaded {len(items)} net exposure rows",
        result={"items": items},
    )


def _execute_audit_events_list(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = AuditEventListToolInput.model_validate(request.input)
    events, next_cursor = AuditTrailService.list_events(
        session,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        start=payload.start,
        end=payload.end,
        cursor=payload.cursor,
        limit=payload.limit,
    )
    result = {
        "events": [AuditEventRead.model_validate(event).model_dump(mode="json") for event in events],
        "next_cursor": next_cursor,
    }
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="audit.events.list",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.read,
        summary=f"Loaded {len(result['events'])} audit events",
        result=result,
    )


def _execute_market_data_cash_settlement_list(
    session: Session,
    request: CapabilityExecutionRequest,
    _context: dict,
    _user: dict,
    execution_id: UUID,
) -> CapabilityExecutionResult:
    payload = MarketDataCashSettlementListInput.model_validate(request.input)
    prices = list_cash_settlement_prices(
        session,
        start_date=payload.start_date,
        end_date=payload.end_date,
        symbol=payload.symbol,
        limit=payload.limit,
    )
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability="market_data.cash_settlement.list",
        status=ExecutionStatus.completed,
        mutability=CapabilityMutability.read,
        summary=f"Loaded {len(prices)} cash-settlement price rows",
        result={"items": [CashSettlementPriceRead.model_validate(price).model_dump(mode='json') for price in prices]},
    )


def _build_capabilities() -> list[CapabilityRegistration]:
    return [
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="audit.events.list",
                domain="audit",
                description="List audit events through the internal capability layer.",
                mutability=CapabilityMutability.read,
                auth_scopes=["auditor"],
                input_schema=AuditEventListToolInput.model_json_schema(),
                tags=["thin-adapter", "audit"],
            ),
            handler=_execute_audit_events_list,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="contracts.list",
                domain="contracts",
                description="List hedge contracts through the internal capability layer.",
                mutability=CapabilityMutability.read,
                auth_scopes=["trader", "risk_manager", "auditor"],
                input_schema=ContractListToolInput.model_json_schema(),
                tags=["thin-adapter", "contracts"],
            ),
            handler=_execute_contracts_list,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="exposures.net",
                domain="exposures",
                description="Compute net exposure through the internal capability layer.",
                mutability=CapabilityMutability.read,
                auth_scopes=["trader", "risk_manager", "auditor"],
                input_schema=ExposureNetToolInput.model_json_schema(),
                tags=["thin-adapter", "exposures"],
            ),
            handler=_execute_exposures_net,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="orders.list",
                domain="orders",
                description="List orders through the internal capability layer.",
                mutability=CapabilityMutability.read,
                auth_scopes=["trader", "risk_manager", "auditor"],
                input_schema=OrderListToolInput.model_json_schema(),
                tags=["thin-adapter", "orders"],
            ),
            handler=_execute_orders_list,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="market_data.cash_settlement.list",
                domain="market_data",
                description="List Westmetall cash-settlement prices through the internal capability layer.",
                mutability=CapabilityMutability.read,
                auth_scopes=["trader", "risk_manager", "auditor"],
                input_schema=MarketDataCashSettlementListInput.model_json_schema(),
                tags=["thin-adapter", "market-data"],
            ),
            handler=_execute_market_data_cash_settlement_list,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="rfq.add_quote",
                domain="rfq",
                description="Create a quote for an RFQ and emit agent audit metadata.",
                mutability=CapabilityMutability.write,
                auth_scopes=["trader"],
                context_entity_type="rfq",
                input_schema=RFQQuoteCreate.model_json_schema(),
                tags=["rfq", "write"],
            ),
            handler=_execute_rfq_add_quote,
            context_builder=build_rfq_context,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="rfq.award",
                domain="rfq",
                description="Award an RFQ using the same business service as the route layer.",
                mutability=CapabilityMutability.write,
                auth_scopes=["trader"],
                context_entity_type="rfq",
                input_schema=RFQAwardRequest.model_json_schema(),
                tags=["rfq", "write"],
            ),
            handler=_execute_rfq_award,
            context_builder=build_rfq_context,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="rfq.create",
                domain="rfq",
                description="Create a new RFQ through the internal capability layer.",
                mutability=CapabilityMutability.write,
                auth_scopes=["trader"],
                idempotent=False,
                input_schema=RFQCreate.model_json_schema(),
                tags=["rfq", "write"],
            ),
            handler=_execute_rfq_create,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="rfq.get",
                domain="rfq",
                description="Load an RFQ and its latest automation context.",
                mutability=CapabilityMutability.read,
                auth_scopes=["trader", "risk_manager", "auditor"],
                context_entity_type="rfq",
                input_schema=RfqIdInput.model_json_schema(),
                tags=["rfq", "read", "context"],
            ),
            handler=_execute_rfq_get,
            context_builder=build_rfq_context,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="rfq.process_inbound_message",
                domain="rfq",
                description="Run the inbound RFQ parsing flow with explicit completion or review semantics.",
                mutability=CapabilityMutability.write,
                auth_scopes=["trader"],
                input_schema=InboundMessageToolInput.model_json_schema(),
                tags=["rfq", "llm", "review"],
            ),
            handler=_execute_rfq_process_inbound,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="rfq.refresh",
                domain="rfq",
                description="Refresh an RFQ and re-send invitations through the service layer.",
                mutability=CapabilityMutability.write,
                auth_scopes=["trader"],
                context_entity_type="rfq",
                input_schema=RFQRefreshRequest.model_json_schema(),
                tags=["rfq", "write"],
            ),
            handler=_execute_rfq_refresh,
            context_builder=build_rfq_context,
        ),
        CapabilityRegistration(
            metadata=CapabilityDefinition(
                name="rfq.reject",
                domain="rfq",
                description="Reject an RFQ through the internal capability layer.",
                mutability=CapabilityMutability.write,
                auth_scopes=["trader"],
                context_entity_type="rfq",
                input_schema=RFQRejectRequest.model_json_schema(),
                tags=["rfq", "write"],
            ),
            handler=_execute_rfq_reject,
            context_builder=build_rfq_context,
        ),
    ]


for capability in _build_capabilities():
    register_capability(capability)


class AgentCapabilityService:
    @staticmethod
    def list_capabilities() -> list[CapabilityDefinition]:
        return [item.metadata for item in iter_capabilities()]

    @staticmethod
    def get_context(
        session: Session,
        capability_name: str,
        *,
        entity_id: UUID | None,
        input_payload: dict[str, Any] | None = None,
    ) -> CapabilityContextResponse:
        if not has_capability(capability_name):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found")
        registration = get_capability(capability_name)
        context = {}
        latest_activity = None
        if registration.context_builder is not None:
            context = registration.context_builder(session, entity_id, input_payload or {})
        if registration.metadata.context_entity_type == "rfq" and entity_id is not None:
            latest_activity = get_latest_agent_activity(
                session,
                entity_type="rfq",
                entity_id=entity_id,
            )
        return CapabilityContextResponse(
            capability=registration.metadata,
            context=context,
            latest_activity=latest_activity,
        )

    @staticmethod
    def execute(
        session: Session,
        request: CapabilityExecutionRequest,
        *,
        user: dict[str, Any],
    ) -> CapabilityExecutionResult:
        if not has_capability(request.capability):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability not found")
        registration = get_capability(request.capability)
        _ensure_roles(user, registration.metadata.auth_scopes)
        context = {}
        if registration.context_builder is not None:
            context = registration.context_builder(session, request.context_entity_id, request.input)
        execution_id = uuid.uuid4()
        if request.actor_id is None:
            request = request.model_copy(update={"actor_id": _actor_id(user, request)})
        return registration.handler(session, request, context, user, execution_id)
