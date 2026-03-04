"""Add text_en and text_pt columns to rfqs table.

Stores the RFQ message texts (English / Portuguese) generated at
preview time so they can be used as the WhatsApp invitation body
— Portuguese for bank_br, English for brokers/others.

Revision ID: 024
Revises: 023
"""

from alembic import op
import sqlalchemy as sa


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rfqs", sa.Column("text_en", sa.Text(), nullable=True))
    op.add_column("rfqs", sa.Column("text_pt", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rfqs", "text_pt")
    op.drop_column("rfqs", "text_en")
