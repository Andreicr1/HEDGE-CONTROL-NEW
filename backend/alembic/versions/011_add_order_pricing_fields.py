"""Add order pricing fields

Revision ID: 011_add_order_pricing_fields
Revises: 010_add_hedge_contract_status
Create Date: 2026-02-01 20:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "011_add_order_pricing_fields"
down_revision: Union[str, None] = "010_add_hedge_contract_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        enum_type = postgresql.ENUM("AVG", "AVGInter", "C2R", name="order_pricing_convention")
        enum_type.create(bind, checkfirst=True)
        op.add_column(
            "orders",
            sa.Column(
                "pricing_convention",
                sa.Enum("AVG", "AVGInter", "C2R", name="order_pricing_convention"),
                nullable=True,
            ),
        )
    else:
        op.add_column("orders", sa.Column("pricing_convention", sa.String(length=32), nullable=True))

    op.add_column("orders", sa.Column("avg_entry_price", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "avg_entry_price")
    op.drop_column("orders", "pricing_convention")

