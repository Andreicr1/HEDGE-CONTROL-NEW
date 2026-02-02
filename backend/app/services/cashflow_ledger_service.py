from __future__ import annotations

import uuid
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.cashflow import CashFlowLedgerEntry, HedgeContractSettlementEvent
from app.models.contracts import HedgeContract, HedgeContractStatus
from app.schemas.cashflow import HedgeContractSettlementCreate, HedgeContractSettlementLeg


SOURCE_EVENT_TYPE = "HEDGE_CONTRACT_SETTLED"


def _normalize_decimal(value: Decimal) -> Decimal:
    return Decimal(str(value))


def _ledger_entry_matches(entry: CashFlowLedgerEntry, expected: dict) -> bool:
    return (
        entry.hedge_contract_id == expected["hedge_contract_id"]
        and entry.source_event_type == expected["source_event_type"]
        and entry.source_event_id == expected["source_event_id"]
        and entry.leg_id == expected["leg_id"]
        and entry.cashflow_date == expected["cashflow_date"]
        and entry.currency == expected["currency"]
        and entry.direction == expected["direction"]
        and _normalize_decimal(entry.amount) == _normalize_decimal(expected["amount"])
    )


def _build_expected_entry(
    contract_id: UUID,
    payload: HedgeContractSettlementCreate,
    leg: HedgeContractSettlementLeg,
) -> dict:
    return {
        "hedge_contract_id": contract_id,
        "source_event_type": SOURCE_EVENT_TYPE,
        "source_event_id": payload.source_event_id,
        "leg_id": leg.leg_id.value,
        "cashflow_date": payload.cashflow_date,
        "currency": "USD",
        "direction": leg.direction.value,
        "amount": leg.amount,
    }


def _assert_contract_active(contract: HedgeContract) -> None:
    if contract.status != HedgeContractStatus.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hedge contract is not active")


def _validate_currency(payload: HedgeContractSettlementCreate) -> None:
    if payload.currency is not None and payload.currency != "USD":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="currency must be USD")


def _raise_conflict() -> None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Settlement ledger conflict")


def ingest_hedge_contract_settlement(
    db: Session,
    contract_id: UUID,
    payload: HedgeContractSettlementCreate,
) -> tuple[HedgeContractSettlementEvent, list[CashFlowLedgerEntry]]:
    contract = db.get(HedgeContract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hedge contract not found")

    _validate_currency(payload)

    existing_event = db.get(HedgeContractSettlementEvent, payload.source_event_id)
    expected_entries = [_build_expected_entry(contract_id, payload, leg) for leg in payload.legs]

    existing_entries = (
        db.query(CashFlowLedgerEntry)
        .filter(
            CashFlowLedgerEntry.source_event_type == SOURCE_EVENT_TYPE,
            CashFlowLedgerEntry.source_event_id == payload.source_event_id,
            CashFlowLedgerEntry.leg_id.in_([leg.leg_id.value for leg in payload.legs]),
            CashFlowLedgerEntry.cashflow_date == payload.cashflow_date,
        )
        .all()
    )

    if contract.status == HedgeContractStatus.settled:
        if existing_event is None or len(existing_entries) != 2:
            _raise_conflict()
        for expected in expected_entries:
            match = next((entry for entry in existing_entries if entry.leg_id == expected["leg_id"]), None)
            if match is None or not _ledger_entry_matches(match, expected):
                _raise_conflict()
        if existing_event.hedge_contract_id != contract_id or existing_event.cashflow_date != payload.cashflow_date:
            _raise_conflict()
        return existing_event, existing_entries

    _assert_contract_active(contract)

    if existing_event is not None:
        if existing_event.hedge_contract_id != contract_id or existing_event.cashflow_date != payload.cashflow_date:
            _raise_conflict()
        if len(existing_entries) != 2:
            _raise_conflict()
        for expected in expected_entries:
            match = next((entry for entry in existing_entries if entry.leg_id == expected["leg_id"]), None)
            if match is None or not _ledger_entry_matches(match, expected):
                _raise_conflict()
        return existing_event, existing_entries

    if existing_entries:
        _raise_conflict()

    settlement_event = HedgeContractSettlementEvent(
        id=payload.source_event_id,
        hedge_contract_id=contract_id,
        cashflow_date=payload.cashflow_date,
    )
    db.add(settlement_event)

    ledger_entries: list[CashFlowLedgerEntry] = []
    for expected in expected_entries:
        entry = CashFlowLedgerEntry(
            id=uuid.uuid4(),
            hedge_contract_id=expected["hedge_contract_id"],
            source_event_type=expected["source_event_type"],
            source_event_id=expected["source_event_id"],
            leg_id=expected["leg_id"],
            cashflow_date=expected["cashflow_date"],
            currency=expected["currency"],
            direction=expected["direction"],
            amount=expected["amount"],
        )
        ledger_entries.append(entry)
        db.add(entry)

    contract.status = HedgeContractStatus.settled
    db.commit()
    db.refresh(settlement_event)
    for entry in ledger_entries:
        db.refresh(entry)

    return settlement_event, ledger_entries