"""Add order pricing detail fields.

counterparty_name, reference_month, observation_date_start,
observation_date_end, fixing_date.

Revision ID: 021
Revises: 020
Create Date: 2026-03-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("counterparty_name", sa.String(200), nullable=True)
    )
    op.add_column("orders", sa.Column("reference_month", sa.String(7), nullable=True))
    op.add_column(
        "orders", sa.Column("observation_date_start", sa.Date(), nullable=True)
    )
    op.add_column("orders", sa.Column("observation_date_end", sa.Date(), nullable=True))
    op.add_column("orders", sa.Column("fixing_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "fixing_date")
    op.drop_column("orders", "observation_date_end")
    op.drop_column("orders", "observation_date_start")
    op.drop_column("orders", "reference_month")
    op.drop_column("orders", "counterparty_name")
