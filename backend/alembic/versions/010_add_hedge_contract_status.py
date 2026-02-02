"""Add hedge contract status

Revision ID: 010_add_hedge_contract_status
Revises: 009_phase4_step2_mtm_snapshots
Create Date: 2026-02-01 20:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "010_add_hedge_contract_status"
down_revision: Union[str, None] = "009_phase4_step2_mtm_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        status_enum = postgresql.ENUM("active", "cancelled", "settled", name="hedge_contract_status")
        status_enum.create(bind, checkfirst=True)
        op.add_column(
            "hedge_contracts",
            sa.Column(
                "status",
                sa.Enum("active", "cancelled", "settled", name="hedge_contract_status"),
                nullable=False,
                server_default="active",
            ),
        )
    else:
        op.add_column("hedge_contracts", sa.Column("status", sa.String(length=32), nullable=False, server_default="active"))

    op.execute("UPDATE hedge_contracts SET status = 'active' WHERE status IS NULL")


def downgrade() -> None:
    op.drop_column("hedge_contracts", "status")
