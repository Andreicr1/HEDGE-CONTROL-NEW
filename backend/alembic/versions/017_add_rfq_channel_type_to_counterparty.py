"""Add rfq_channel_type to counterparties table.

Revision ID: 017
Revises: 016
"""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    rfq_channel_type = sa.Enum("broker_lme", "banco_br", "none", name="rfq_channel_type")
    rfq_channel_type.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "counterparties",
        sa.Column(
            "rfq_channel_type",
            rfq_channel_type,
            nullable=False,
            server_default="none",
        ),
    )


def downgrade() -> None:
    op.drop_column("counterparties", "rfq_channel_type")
    sa.Enum(name="rfq_channel_type").drop(op.get_bind(), checkfirst=True)
