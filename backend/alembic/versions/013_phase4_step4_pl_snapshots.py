"""Revision ID: 013_phase4_step4_pl_snapshots
Revises: 012_phase4_step3_cashflow_baseline_snapshots

Migration for P&L Snapshots Table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# Revision identifiers, used by Alembic
revision = '013_phase4_step4_pl_snapshots'
down_revision = '012_phase4_step3_cashflow_baseline_snapshots'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'pl_snapshots',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('entity_type', sa.String, nullable=False),
        sa.Column('entity_id', UUID(as_uuid=True), nullable=False),
        sa.Column('period_start', sa.Date, nullable=False),
        sa.Column('period_end', sa.Date, nullable=False),
        sa.Column('realized_pl', sa.Numeric(18, 6), nullable=False),
        sa.Column('unrealized_mtm', sa.Numeric(18, 6), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('correlation_id', UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint('entity_type', 'entity_id', 'period_start', 'period_end', name='uq_pl_snapshot_entity_period')
    )

def downgrade():
    op.drop_table('pl_snapshots')