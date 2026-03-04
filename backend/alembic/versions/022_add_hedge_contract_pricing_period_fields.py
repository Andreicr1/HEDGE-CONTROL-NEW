"""Add pricing period fields to hedge_contracts.

These columns exist in the HedgeContract model but were never added via
migration, causing ``UndefinedColumn`` errors on PostgreSQL in production.

Revision ID: 022_add_hedge_contract_pricing_period_fields
Revises: 021_add_order_pricing_detail_fields
Create Date: 2026-03-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    new_cols = [
        sa.Column(
            "pricing_period_month",
            sa.Integer(),
            nullable=True,
            comment="Reference month for avg convention (1-12)",
        ),
        sa.Column(
            "pricing_period_year",
            sa.Integer(),
            nullable=True,
            comment="Reference year for avg convention",
        ),
        sa.Column(
            "fixing_date",
            sa.Date(),
            nullable=True,
            comment="Fixing date for c2r convention",
        ),
        sa.Column(
            "avg_computation_days",
            sa.Integer(),
            nullable=True,
            comment="Number of days for avginter convention",
        ),
    ]

    if is_pg:
        for col in new_cols:
            op.add_column("hedge_contracts", col)
    else:
        with op.batch_alter_table("hedge_contracts") as batch:
            for col in new_cols:
                batch.add_column(col)


def downgrade() -> None:
    for col_name in [
        "avg_computation_days",
        "fixing_date",
        "pricing_period_year",
        "pricing_period_month",
    ]:
        op.drop_column("hedge_contracts", col_name)
