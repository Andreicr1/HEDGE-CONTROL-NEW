"""Create RFQ quotes table

Revision ID: 005_create_rfq_quotes_table
Revises: 004_create_rfq_tables
Create Date: 2026-02-01 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_create_rfq_quotes_table"
down_revision: Union[str, None] = "004_create_rfq_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rfq_quotes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("rfq_id", sa.Uuid(), nullable=False),
        sa.Column("counterparty_id", sa.String(length=64), nullable=False),
        sa.Column("price_value", sa.Float(), nullable=False),
        sa.Column("price_unit", sa.String(length=32), nullable=False),
        sa.Column("pricing_convention", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("rfq_quotes")
