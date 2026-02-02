import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, JSON, Numeric, String, UniqueConstraint, Table, MetaData, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base

metadata = MetaData()

class CashFlowBaselineSnapshot(Base):
    __tablename__ = "cashflow_baseline_snapshots"
    __table_args__ = (
        UniqueConstraint("as_of_date", name="uq_cashflow_baseline_snapshots_as_of_date"),
        {"extend_existing": True},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_net_cashflow: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(length=64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class HedgeContractSettlementEvent(Base):
    __tablename__ = "hedge_contract_settlement_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    hedge_contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hedge_contracts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    cashflow_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CashFlowLedgerEntry(Base):
    __tablename__ = "cashflow_ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "source_event_type",
            "source_event_id",
            "leg_id",
            "cashflow_date",
            name="uq_cashflow_ledger_entry_event_leg_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hedge_contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hedge_contracts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_event_type: Mapped[str] = mapped_column(String(length=64), nullable=False)
    source_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hedge_contract_settlement_events.id", ondelete="RESTRICT"),
        nullable=True,
    )
    leg_id: Mapped[str] = mapped_column(String(length=16), nullable=False)
    cashflow_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(length=8), nullable=False)
    direction: Mapped[str] = mapped_column(String(length=8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
