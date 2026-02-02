"""Revision ID: 014_phase5_step1_cashflow_ledger
Revises: 013_phase4_step4_pl_snapshots

Migration for CashFlow Ledger and Hedge Contract Settlement Events.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# Revision identifiers, used by Alembic
revision = '014_phase5_step1_cashflow_ledger'
down_revision = '013_phase4_step4_pl_snapshots'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'hedge_contract_settlement_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('hedge_contract_id', UUID(as_uuid=True), sa.ForeignKey('hedge_contracts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('cashflow_date', sa.Date, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )

    op.create_table(
        'cashflow_ledger_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('hedge_contract_id', UUID(as_uuid=True), sa.ForeignKey('hedge_contracts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('source_event_type', sa.String, nullable=False),
        sa.Column('source_event_id', UUID(as_uuid=True), sa.ForeignKey('hedge_contract_settlement_events.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('leg_id', sa.String, nullable=False),
        sa.Column('cashflow_date', sa.Date, nullable=False),
        sa.Column('currency', sa.String, nullable=False),
        sa.Column('direction', sa.String, nullable=False),
        sa.Column('amount', sa.Numeric(18, 6), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.UniqueConstraint('source_event_type', 'source_event_id', 'leg_id', 'cashflow_date', name='uq_cashflow_ledger_entry_event_leg_date'),
    )


def downgrade():
    op.drop_table('cashflow_ledger_entries')
    op.drop_table('hedge_contract_settlement_events')