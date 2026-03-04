"""Add unique constraint on deal_links (linked_type, linked_id).

Each order or hedge contract may belong to only one deal.

Revision ID: 020
Revises: 019
Create Date: 2026-03-03
"""

from typing import Sequence, Union

from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_deal_link_entity",
        "deal_links",
        ["linked_type", "linked_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_deal_link_entity", "deal_links", type_="unique")
