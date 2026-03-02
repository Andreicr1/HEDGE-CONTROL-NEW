"""Hedge service — CRUD + lifecycle + RFQ integration."""

from __future__ import annotations

import uuid as _uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.exposure import HedgeExposure, Exposure, ExposureStatus
from app.models.hedge import Hedge, HedgeDirection, HedgeSourceType, HedgeStatus
from app.models.rfqs import RFQ, RFQState


def _generate_reference() -> str:
    """Generate a unique hedge reference like H-XXXXXXXX."""
    return f"H-{_uuid.uuid4().hex[:8].upper()}"


# Valid status transitions
_VALID_TRANSITIONS: dict[HedgeStatus, set[HedgeStatus]] = {
    HedgeStatus.active: {
        HedgeStatus.partially_settled,
        HedgeStatus.settled,
        HedgeStatus.cancelled,
    },
    HedgeStatus.partially_settled: {HedgeStatus.settled, HedgeStatus.cancelled},
    HedgeStatus.settled: set(),  # terminal
    HedgeStatus.cancelled: set(),  # terminal
}


class HedgeService:
    """Stateless service for Hedge operations."""

    @staticmethod
    def create_hedge(
        session: Session, data: dict, created_by: str | None = None
    ) -> Hedge:
        """Create a new hedge and optionally link to an exposure."""
        exposure_id = data.pop("exposure_id", None)
        trade_date = data.get("trade_date") or date.today()

        hedge = Hedge(
            reference=_generate_reference(),
            counterparty_id=data["counterparty_id"],
            commodity=data["commodity"],
            direction=HedgeDirection(data["direction"]),
            tons=data["tons"],
            price_per_ton=data["price_per_ton"],
            premium_discount=data.get("premium_discount", 0),
            settlement_date=data["settlement_date"],
            prompt_date=data.get("prompt_date"),
            trade_date=trade_date,
            status=HedgeStatus.active,
            source_type=HedgeSourceType(data.get("source_type", "manual")),
            source_id=data.get("source_id"),
            contract_id=data.get("contract_id"),
            notes=data.get("notes"),
            created_by=created_by,
        )
        session.add(hedge)
        session.flush()  # get hedge.id

        # Link to exposure if provided
        if exposure_id:
            exp = session.query(Exposure).filter(Exposure.id == exposure_id).first()
            if exp:
                link = HedgeExposure(
                    exposure_id=exposure_id,
                    hedge_id=hedge.id,
                    allocated_tons=data["tons"],
                )
                session.add(link)
                # Update exposure open_tons
                exp.open_tons = max(0, float(exp.open_tons) - float(data["tons"]))
                if exp.open_tons <= 0:
                    exp.status = ExposureStatus.fully_hedged
                else:
                    exp.status = ExposureStatus.partially_hedged

        session.commit()
        session.refresh(hedge)
        return hedge

    @staticmethod
    def create_from_rfq_award(
        session: Session, rfq_id: _uuid.UUID, created_by: str | None = None
    ) -> Hedge:
        """Create a hedge from an awarded RFQ."""
        rfq = session.query(RFQ).filter(RFQ.id == rfq_id).first()
        if not rfq:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found"
            )
        if rfq.state != RFQState.awarded:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"RFQ state is {rfq.state.value}, must be AWARDED",
            )

        direction = (
            HedgeDirection.buy if rfq.direction.value == "BUY" else HedgeDirection.sell
        )

        hedge = Hedge(
            reference=_generate_reference(),
            counterparty_id=_uuid.uuid4(),  # placeholder — should come from RFQ winner
            commodity=rfq.commodity,
            direction=direction,
            tons=rfq.quantity_mt,
            price_per_ton=0,  # from awarded quote — simplified
            premium_discount=0,
            settlement_date=rfq.delivery_window_end,
            trade_date=date.today(),
            status=HedgeStatus.active,
            source_type=HedgeSourceType.rfq_award,
            source_id=rfq.id,
            created_by=created_by,
        )
        session.add(hedge)
        session.commit()
        session.refresh(hedge)
        return hedge

    @staticmethod
    def list_hedges(
        session: Session,
        commodity: str | None = None,
        status_filter: str | None = None,
        counterparty_id: _uuid.UUID | None = None,
    ):
        """Return query for hedges with filters."""
        q = session.query(Hedge).filter(Hedge.is_deleted == False)  # noqa: E712
        if commodity:
            q = q.filter(Hedge.commodity == commodity)
        if status_filter:
            q = q.filter(Hedge.status == HedgeStatus(status_filter))
        if counterparty_id:
            q = q.filter(Hedge.counterparty_id == counterparty_id)
        return q.order_by(Hedge.created_at.desc())

    @staticmethod
    def get_by_id(session: Session, hedge_id: _uuid.UUID) -> Hedge | None:
        return (
            session.query(Hedge)
            .filter(Hedge.id == hedge_id, Hedge.is_deleted == False)  # noqa: E712
            .first()
        )

    @staticmethod
    def update_hedge(session: Session, hedge_id: _uuid.UUID, data: dict) -> Hedge:
        hedge = HedgeService.get_by_id(session, hedge_id)
        if not hedge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Hedge not found"
            )
        for key, value in data.items():
            if value is not None:
                setattr(hedge, key, value)
        session.commit()
        session.refresh(hedge)
        return hedge

    @staticmethod
    def update_status(
        session: Session, hedge_id: _uuid.UUID, new_status: HedgeStatus
    ) -> Hedge:
        hedge = HedgeService.get_by_id(session, hedge_id)
        if not hedge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Hedge not found"
            )

        if new_status not in _VALID_TRANSITIONS.get(hedge.status, set()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot transition from {hedge.status.value} to {new_status.value}",
            )
        hedge.status = new_status
        session.commit()
        session.refresh(hedge)
        return hedge

    @staticmethod
    def cancel_hedge(session: Session, hedge_id: _uuid.UUID) -> Hedge:
        """Soft delete + cancel + release exposure tons."""
        hedge = HedgeService.get_by_id(session, hedge_id)
        if not hedge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Hedge not found"
            )

        hedge.status = HedgeStatus.cancelled
        hedge.is_deleted = True
        hedge.deleted_at = datetime.now(timezone.utc)

        # Release exposure tons
        links = (
            session.query(HedgeExposure)
            .filter(HedgeExposure.hedge_id == hedge_id)
            .all()
        )
        for link in links:
            exp = (
                session.query(Exposure).filter(Exposure.id == link.exposure_id).first()
            )
            if exp:
                exp.open_tons = float(exp.open_tons) + float(link.allocated_tons)
                if exp.open_tons >= float(exp.original_tons):
                    exp.status = ExposureStatus.open
                else:
                    exp.status = ExposureStatus.partially_hedged

        session.commit()
        session.refresh(hedge)
        return hedge
