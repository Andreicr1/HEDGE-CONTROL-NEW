"""Create orders table

Revision ID: 001_create_orders_table
Revises: None
Create Date: 2026-02-01 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_create_orders_table"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


order_type_enum = postgresql.ENUM("SO", "PO", name="order_type")
price_type_enum = postgresql.ENUM("fixed", "variable", name="price_type")


def upgrade() -> None:
    order_type_enum.create(op.get_bind(), checkfirst=True)
    price_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("order_type", sa.Enum("SO", "PO", name="order_type"), nullable=False),
        sa.Column("price_type", sa.Enum("fixed", "variable", name="price_type"), nullable=False),
        sa.Column("quantity_mt", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("orders")
    price_type_enum.drop(op.get_bind(), checkfirst=True)
    order_type_enum.drop(op.get_bind(), checkfirst=True)
