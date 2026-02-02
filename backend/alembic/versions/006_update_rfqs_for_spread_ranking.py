"""Update RFQs for spread ranking

Revision ID: 006_update_rfqs_for_spread_ranking
Revises: 005_create_rfq_quotes_table
Create Date: 2026-02-01 16:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "006_update_rfqs_for_spread_ranking"
down_revision: Union[str, None] = "005_create_rfq_quotes_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE rfq_intent ADD VALUE IF NOT EXISTS 'SPREAD'")

    op.add_column("rfqs", sa.Column("buy_trade_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("rfqs", sa.Column("sell_trade_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_rfqs_buy_trade_id_rfqs",
        "rfqs",
        "rfqs",
        ["buy_trade_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_rfqs_sell_trade_id_rfqs",
        "rfqs",
        "rfqs",
        ["sell_trade_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.add_column("rfq_state_events", sa.Column("trigger", sa.String(length=64), nullable=True))
    op.add_column(
        "rfq_state_events",
        sa.Column("triggering_quote_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "rfq_state_events",
        sa.Column("triggering_counterparty_id", sa.String(length=64), nullable=True),
    )
    op.add_column("rfq_state_events", sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("rfq_state_events", "event_timestamp")
    op.drop_column("rfq_state_events", "triggering_counterparty_id")
    op.drop_column("rfq_state_events", "triggering_quote_id")
    op.drop_column("rfq_state_events", "trigger")

    op.drop_constraint("fk_rfqs_sell_trade_id_rfqs", "rfqs", type_="foreignkey")
    op.drop_constraint("fk_rfqs_buy_trade_id_rfqs", "rfqs", type_="foreignkey")
    op.drop_column("rfqs", "sell_trade_id")
    op.drop_column("rfqs", "buy_trade_id")

    # rfq_intent enum value SPREAD is not removed on downgrade for PostgreSQL.

