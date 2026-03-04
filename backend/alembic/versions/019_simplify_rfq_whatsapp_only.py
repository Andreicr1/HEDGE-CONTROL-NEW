"""Simplify RFQ to WhatsApp-only and add whatsapp_phone to counterparties.

This migration:
  1. Adds whatsapp_phone column to counterparties table
  2. Drops rfq_channel_type column from counterparties table
  3. Adds counterparty_id (UUID FK) and recipient_phone columns to rfq_invitations
  4. Copies existing recipient_id values into recipient_phone for data continuity
  5. Drops the old recipient_id column from rfq_invitations

Revision ID: 019
Revises: 018
"""

from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # --- 1. counterparties: add whatsapp_phone ---
    op.add_column(
        "counterparties",
        sa.Column("whatsapp_phone", sa.String(50), nullable=True),
    )

    # --- 2. counterparties: drop rfq_channel_type ---
    if is_sqlite:
        # SQLite: batch mode needed
        with op.batch_alter_table("counterparties") as batch_op:
            batch_op.drop_column("rfq_channel_type")
    else:
        op.drop_column("counterparties", "rfq_channel_type")
        sa.Enum(name="rfq_channel_type").drop(bind, checkfirst=True)

    # --- 3. rfq_invitations: add counterparty_id and recipient_phone ---
    op.add_column(
        "rfq_invitations",
        sa.Column("counterparty_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "rfq_invitations",
        sa.Column("recipient_phone", sa.String(50), nullable=True),
    )

    # Copy existing recipient_id values into recipient_phone for data continuity
    op.execute(
        "UPDATE rfq_invitations SET recipient_phone = recipient_id WHERE recipient_id IS NOT NULL"
    )

    # --- 4. rfq_invitations: drop old recipient_id ---
    if is_sqlite:
        with op.batch_alter_table("rfq_invitations") as batch_op:
            batch_op.drop_column("recipient_id")
    else:
        op.drop_column("rfq_invitations", "recipient_id")

    # --- 5. Add FK constraint for counterparty_id (PostgreSQL only; SQLite auto-handles) ---
    if not is_sqlite:
        op.create_foreign_key(
            "fk_rfq_invitations_counterparty_id",
            "rfq_invitations",
            "counterparties",
            ["counterparty_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Restore recipient_id column
    op.add_column(
        "rfq_invitations",
        sa.Column("recipient_id", sa.String(64), nullable=True),
    )

    # Copy recipient_phone back to recipient_id
    op.execute(
        "UPDATE rfq_invitations SET recipient_id = recipient_phone WHERE recipient_phone IS NOT NULL"
    )

    # Drop new columns
    if is_sqlite:
        with op.batch_alter_table("rfq_invitations") as batch_op:
            batch_op.drop_column("recipient_phone")
            batch_op.drop_column("counterparty_id")
    else:
        op.drop_constraint(
            "fk_rfq_invitations_counterparty_id",
            "rfq_invitations",
            type_="foreignkey",
        )
        op.drop_column("rfq_invitations", "recipient_phone")
        op.drop_column("rfq_invitations", "counterparty_id")

    # Restore rfq_channel_type on counterparties
    if is_sqlite:
        with op.batch_alter_table("counterparties") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "rfq_channel_type",
                    sa.String(20),
                    nullable=True,
                    server_default="none",
                )
            )
    else:
        rfq_channel_type = sa.Enum(
            "broker_lme", "banco_br", "none", name="rfq_channel_type"
        )
        rfq_channel_type.create(bind, checkfirst=True)
        op.add_column(
            "counterparties",
            sa.Column(
                "rfq_channel_type",
                rfq_channel_type,
                nullable=False,
                server_default="none",
            ),
        )

    # Drop whatsapp_phone
    op.drop_column("counterparties", "whatsapp_phone")
