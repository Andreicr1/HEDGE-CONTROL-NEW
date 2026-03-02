"""Add soft-delete (deleted_at) to orders, hedge_contracts, rfqs.

Revision ID: 016
Revises: 015
"""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015_phase7_audit_events_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "hedge_contracts",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "rfqs", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("rfqs", "deleted_at")
    op.drop_column("hedge_contracts", "deleted_at")
    op.drop_column("orders", "deleted_at")
