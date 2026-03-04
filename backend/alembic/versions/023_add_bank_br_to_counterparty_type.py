"""Add bank_br value to counterparty_type enum.

The Python model includes ``bank_br`` but the PostgreSQL enum type created in
the initial migration only had ``customer``, ``supplier``, ``broker``.

Revision ID: 023
Revises: 022
Create Date: 2026-03-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # ALTER TYPE ... ADD VALUE is not transactional in PG < 12 so we
    # execute it outside the current transaction if necessary.
    op.execute("ALTER TYPE counterparty_type ADD VALUE IF NOT EXISTS 'bank_br'")


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum type.
    # A full recreate would be needed which is out of scope here.
    pass
