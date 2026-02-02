"""Phase 3 Step 3 award and contract fields

Revision ID: 007_phase3_step3_award_and_contract_fields
Revises: 006_update_rfqs_for_spread_ranking
Create Date: 2026-02-01 18:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "007_phase3_step3_award_and_contract_fields"
down_revision: Union[str, None] = "006_update_rfqs_for_spread_ranking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE rfq_state ADD VALUE IF NOT EXISTS 'AWARDED'")
        op.execute("ALTER TYPE rfq_state ADD VALUE IF NOT EXISTS 'CLOSED'")

    op.add_column("rfq_state_events", sa.Column("user_id", sa.String(length=64), nullable=True))
    op.add_column("rfq_state_events", sa.Column("reason", sa.String(length=128), nullable=True))
    op.add_column("rfq_state_events", sa.Column("ranking_snapshot", sa.Text(), nullable=True))
    op.add_column("rfq_state_events", sa.Column("winning_quote_ids", sa.Text(), nullable=True))
    op.add_column("rfq_state_events", sa.Column("winning_counterparty_ids", sa.Text(), nullable=True))
    op.add_column("rfq_state_events", sa.Column("award_timestamp", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rfq_state_events", sa.Column("created_contract_ids", sa.Text(), nullable=True))

    op.add_column("hedge_contracts", sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("hedge_contracts", sa.Column("rfq_quote_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("hedge_contracts", sa.Column("counterparty_id", sa.String(length=64), nullable=True))
    op.add_column("hedge_contracts", sa.Column("fixed_price_value", sa.Float(), nullable=True))
    op.add_column("hedge_contracts", sa.Column("fixed_price_unit", sa.String(length=32), nullable=True))
    op.add_column("hedge_contracts", sa.Column("float_pricing_convention", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_hedge_contracts_rfq_id_rfqs",
        "hedge_contracts",
        "rfqs",
        ["rfq_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_hedge_contracts_rfq_quote_id_rfq_quotes",
        "hedge_contracts",
        "rfq_quotes",
        ["rfq_quote_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_hedge_contracts_rfq_quote_id_rfq_quotes", "hedge_contracts", type_="foreignkey")
    op.drop_constraint("fk_hedge_contracts_rfq_id_rfqs", "hedge_contracts", type_="foreignkey")
    op.drop_column("hedge_contracts", "float_pricing_convention")
    op.drop_column("hedge_contracts", "fixed_price_unit")
    op.drop_column("hedge_contracts", "fixed_price_value")
    op.drop_column("hedge_contracts", "counterparty_id")
    op.drop_column("hedge_contracts", "rfq_quote_id")
    op.drop_column("hedge_contracts", "rfq_id")

    op.drop_column("rfq_state_events", "created_contract_ids")
    op.drop_column("rfq_state_events", "award_timestamp")
    op.drop_column("rfq_state_events", "winning_counterparty_ids")
    op.drop_column("rfq_state_events", "winning_quote_ids")
    op.drop_column("rfq_state_events", "ranking_snapshot")
    op.drop_column("rfq_state_events", "reason")
    op.drop_column("rfq_state_events", "user_id")

    # rfq_state enum values are not removed on downgrade for PostgreSQL.

