"""Phase 4 Step 3 CashFlow baseline snapshots

Revision ID: 012_phase4_step3_cashflow_baseline_snapshots
Revises: 011_add_order_pricing_fields
Create Date: 2026-02-01 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "012_phase4_step3_cashflow_baseline_snapshots"
down_revision: Union[str, None] = "011_add_order_pricing_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cashflow_baseline_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("total_net_cashflow", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("as_of_date", name="uq_cashflow_baseline_snapshots_as_of_date"),
    )


def downgrade() -> None:
    op.drop_table("cashflow_baseline_snapshots")

