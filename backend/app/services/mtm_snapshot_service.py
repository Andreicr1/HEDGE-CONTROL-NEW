from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.mtm import MTMObjectType, MTMSnapshot
from app.services.mtm_contract_service import compute_mtm_for_contract
from app.services.mtm_order_service import compute_mtm_for_order


def _as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def create_mtm_snapshot_for_contract(db: Session, contract_id: UUID, as_of_date: date, correlation_id: str) -> MTMSnapshot:
    existing = (
        db.query(MTMSnapshot)
        .filter(
            MTMSnapshot.object_type == MTMObjectType.hedge_contract,
            MTMSnapshot.object_id == contract_id,
            MTMSnapshot.as_of_date == as_of_date,
        )
        .first()
    )

    computed = compute_mtm_for_contract(db, contract_id=contract_id, as_of_date=as_of_date)

    if existing is not None:
        if (
            _as_decimal(existing.mtm_value) != _as_decimal(computed.mtm_value)
            or _as_decimal(existing.price_d1) != _as_decimal(computed.price_d1)
            or _as_decimal(existing.entry_price) != _as_decimal(computed.entry_price)
            or _as_decimal(existing.quantity_mt) != _as_decimal(computed.quantity_mt)
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MTM snapshot conflict")
        return existing

    snapshot = MTMSnapshot(
        object_type=MTMObjectType.hedge_contract,
        object_id=contract_id,
        as_of_date=as_of_date,
        mtm_value=_as_decimal(computed.mtm_value),
        price_d1=_as_decimal(computed.price_d1),
        entry_price=_as_decimal(computed.entry_price),
        quantity_mt=_as_decimal(computed.quantity_mt),
        correlation_id=correlation_id,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def create_mtm_snapshot_for_order(db: Session, order_id: UUID, as_of_date: date, correlation_id: str) -> MTMSnapshot:
    existing = (
        db.query(MTMSnapshot)
        .filter(
            MTMSnapshot.object_type == MTMObjectType.order,
            MTMSnapshot.object_id == order_id,
            MTMSnapshot.as_of_date == as_of_date,
        )
        .first()
    )

    computed = compute_mtm_for_order(db, order_id=order_id, as_of_date=as_of_date)

    if existing is not None:
        if (
            _as_decimal(existing.mtm_value) != _as_decimal(computed.mtm_value)
            or _as_decimal(existing.price_d1) != _as_decimal(computed.price_d1)
            or _as_decimal(existing.entry_price) != _as_decimal(computed.entry_price)
            or _as_decimal(existing.quantity_mt) != _as_decimal(computed.quantity_mt)
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MTM snapshot conflict")
        return existing

    snapshot = MTMSnapshot(
        object_type=MTMObjectType.order,
        object_id=order_id,
        as_of_date=as_of_date,
        mtm_value=_as_decimal(computed.mtm_value),
        price_d1=_as_decimal(computed.price_d1),
        entry_price=_as_decimal(computed.entry_price),
        quantity_mt=_as_decimal(computed.quantity_mt),
        correlation_id=correlation_id,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot
