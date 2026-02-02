"""Create RFQ tables

Revision ID: 004_create_rfq_tables
Revises: 003_create_hedge_order_linkages_table
Create Date: 2026-02-01 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_create_rfq_tables"
down_revision: Union[str, None] = "003_create_hedge_order_linkages_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


rfq_intent_enum = postgresql.ENUM("COMMERCIAL_HEDGE", "GLOBAL_POSITION", name="rfq_intent")
rfq_direction_enum = postgresql.ENUM("BUY", "SELL", name="rfq_direction")
rfq_state_enum = postgresql.ENUM("CREATED", "SENT", "QUOTED", name="rfq_state")
rfq_invitation_channel_enum = postgresql.ENUM(
    "email",
    "api",
    "whatsapp",
    "bank",
    "broker",
    "other",
    name="rfq_invitation_channel",
)
rfq_invitation_status_enum = postgresql.ENUM(
    "queued", "sent", "failed", name="rfq_invitation_status"
)


def upgrade() -> None:
    rfq_intent_enum.create(op.get_bind(), checkfirst=True)
    rfq_direction_enum.create(op.get_bind(), checkfirst=True)
    rfq_state_enum.create(op.get_bind(), checkfirst=True)
    rfq_invitation_channel_enum.create(op.get_bind(), checkfirst=True)
    rfq_invitation_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "rfq_sequences",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
    )

    op.create_table(
        "rfqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rfq_number", sa.String(length=32), nullable=False, unique=True),
        sa.Column("intent", sa.Enum("COMMERCIAL_HEDGE", "GLOBAL_POSITION", name="rfq_intent"), nullable=False),
        sa.Column("commodity", sa.String(length=64), nullable=False),
        sa.Column("quantity_mt", sa.Float(), nullable=False),
        sa.Column("delivery_window_start", sa.Date(), nullable=False),
        sa.Column("delivery_window_end", sa.Date(), nullable=False),
        sa.Column("direction", sa.Enum("BUY", "SELL", name="rfq_direction"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("commercial_active_mt", sa.Float(), nullable=False),
        sa.Column("commercial_passive_mt", sa.Float(), nullable=False),
        sa.Column("commercial_net_mt", sa.Float(), nullable=False),
        sa.Column("commercial_reduction_applied_mt", sa.Float(), nullable=False),
        sa.Column("exposure_snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.Enum("CREATED", "SENT", "QUOTED", name="rfq_state"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "rfq_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_number", sa.String(length=32), nullable=False),
        sa.Column("recipient_id", sa.String(length=64), nullable=False),
        sa.Column("recipient_name", sa.String(length=128), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(
                "email",
                "api",
                "whatsapp",
                "bank",
                "broker",
                "other",
                name="rfq_invitation_channel",
            ),
            nullable=False,
        ),
        sa.Column("message_body", sa.Text(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=128), nullable=False),
        sa.Column(
            "send_status",
            sa.Enum("queued", "sent", "failed", name="rfq_invitation_status"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"], ondelete="RESTRICT"),
    )

    op.create_table(
        "rfq_state_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_state", sa.Enum("CREATED", "SENT", "QUOTED", name="rfq_state"), nullable=False),
        sa.Column("to_state", sa.Enum("CREATED", "SENT", "QUOTED", name="rfq_state"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"], ondelete="RESTRICT"),
    )


def downgrade() -> None:
    op.drop_table("rfq_state_events")
    op.drop_table("rfq_invitations")
    op.drop_table("rfqs")
    op.drop_table("rfq_sequences")

    rfq_invitation_status_enum.drop(op.get_bind(), checkfirst=True)
    rfq_invitation_channel_enum.drop(op.get_bind(), checkfirst=True)
    rfq_state_enum.drop(op.get_bind(), checkfirst=True)
    rfq_direction_enum.drop(op.get_bind(), checkfirst=True)
    rfq_intent_enum.drop(op.get_bind(), checkfirst=True)
