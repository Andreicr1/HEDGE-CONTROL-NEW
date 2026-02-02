"""Phase 4 Step 2 MTM snapshots

Revision ID: 009_phase4_step2_mtm_snapshots
Revises: 008_create_cash_settlement_prices
Create Date: 2026-02-01 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "009_phase4_step2_mtm_snapshots"
down_revision: Union[str, None] = "008_create_cash_settlement_prices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mtm_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("object_type", sa.Enum("hedge_contract", "order", name="mtm_object_type"), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("mtm_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("price_d1", sa.Numeric(18, 6), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_mt", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("object_type", "object_id", "as_of_date", name="uq_mtm_snapshots_object_type_id_as_of"),
    )


def downgrade() -> None:
    op.drop_table("mtm_snapshots")

