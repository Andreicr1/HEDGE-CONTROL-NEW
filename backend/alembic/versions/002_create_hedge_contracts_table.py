"""Create hedge contracts table

Revision ID: 002_create_hedge_contracts_table
Revises: 001_create_orders_table
Create Date: 2026-02-01 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_create_hedge_contracts_table"
down_revision: Union[str, None] = "001_create_orders_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


hedge_leg_side_enum = postgresql.ENUM("buy", "sell", name="hedge_leg_side")
hedge_classification_enum = postgresql.ENUM("long", "short", name="hedge_classification")


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if is_postgres:
        hedge_leg_side_enum.create(bind, checkfirst=True)
        hedge_classification_enum.create(bind, checkfirst=True)

    enum_kwargs = {} if is_postgres else {"native_enum": False, "create_constraint": True}

    op.create_table(
        "hedge_contracts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("commodity", sa.String(length=64), nullable=False),
        sa.Column("quantity_mt", sa.Float(), nullable=False),
        sa.Column(
            "fixed_leg_side",
            sa.Enum("buy", "sell", name="hedge_leg_side", **enum_kwargs),
            nullable=False,
        ),
        sa.Column(
            "variable_leg_side",
            sa.Enum("buy", "sell", name="hedge_leg_side", **enum_kwargs),
            nullable=False,
        ),
        sa.Column(
            "classification",
            sa.Enum("long", "short", name="hedge_classification", **enum_kwargs),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("hedge_contracts")
    hedge_classification_enum.drop(op.get_bind(), checkfirst=True)
    hedge_leg_side_enum.drop(op.get_bind(), checkfirst=True)
