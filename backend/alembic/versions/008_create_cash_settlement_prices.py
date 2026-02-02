"""Create cash settlement prices

Revision ID: 008_create_cash_settlement_prices
Revises: 007_phase3_step3_award_and_contract_fields
Create Date: 2026-02-01 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "008_create_cash_settlement_prices"
down_revision: Union[str, None] = "007_phase3_step3_award_and_contract_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cash_settlement_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("price_usd", sa.Float(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("html_sha256", sa.String(length=64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("source", "symbol", "settlement_date", name="uq_cash_settlement_prices_source_symbol_date"),
    )


def downgrade() -> None:
    op.drop_table("cash_settlement_prices")

