"""Create hedge order linkages table

Revision ID: 003_create_hedge_order_linkages_table
Revises: 002_create_hedge_contracts_table
Create Date: 2026-02-01 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_create_hedge_order_linkages_table"
down_revision: Union[str, None] = "002_create_hedge_contracts_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hedge_order_linkages",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("quantity_mt", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contract_id"], ["hedge_contracts.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("hedge_order_linkages")
