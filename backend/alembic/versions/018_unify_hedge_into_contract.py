"""Unify Hedge into HedgeContract — absorb all Hedge fields, drop hedges table.

This migration:
  1. Merges the two branched heads (017 and 88c13cd6dd8e)
  2. Adds partially_settled to hedge_contract_status enum
  3. Expands counterparty_id from VARCHAR(64) to VARCHAR(100)
  4. Adds new columns to hedge_contracts:
     reference, premium_discount, settlement_date, prompt_date, trade_date,
     source_type, source_id, notes, created_by, updated_at
  5. Migrates existing data from hedges → hedge_contracts
  6. Drops the now-redundant hedges table

Revision ID: 018_unify_hedge_into_contract
Revises: 017, 88c13cd6dd8e
Create Date: 2026-03-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: tuple = ("017", "88c13cd6dd8e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ------------------------------------------------------------------
    # 1. Add 'partially_settled' to hedge_contract_status enum (PG only)
    # ------------------------------------------------------------------
    if is_pg:
        op.execute(
            "ALTER TYPE hedge_contract_status ADD VALUE IF NOT EXISTS 'partially_settled'"
        )

    # ------------------------------------------------------------------
    # 2. Expand counterparty_id from VARCHAR(64) to VARCHAR(100)
    # ------------------------------------------------------------------
    if is_pg:
        op.alter_column(
            "hedge_contracts",
            "counterparty_id",
            existing_type=sa.String(64),
            type_=sa.String(100),
            existing_nullable=True,
        )
    else:
        # SQLite: batch mode for alter column
        with op.batch_alter_table("hedge_contracts") as batch:
            batch.alter_column(
                "counterparty_id",
                existing_type=sa.String(64),
                type_=sa.String(100),
                existing_nullable=True,
            )

    # ------------------------------------------------------------------
    # 3. Add new columns to hedge_contracts
    # ------------------------------------------------------------------
    new_cols = [
        sa.Column("reference", sa.String(50), unique=True, nullable=True),
        sa.Column("premium_discount", sa.Float(), nullable=True, server_default="0"),
        sa.Column("settlement_date", sa.Date(), nullable=True),
        sa.Column("prompt_date", sa.Date(), nullable=True),
        sa.Column("trade_date", sa.Date(), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]

    if is_pg:
        for col in new_cols:
            op.add_column("hedge_contracts", col)
    else:
        with op.batch_alter_table("hedge_contracts") as batch:
            for col in new_cols:
                batch.add_column(col)

    # ------------------------------------------------------------------
    # 4. Migrate data from hedges → hedge_contracts (best effort)
    #    Only copies hedges that don't already have a matching contract_id.
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO hedge_contracts (
            id, commodity, quantity_mt, fixed_leg_side, variable_leg_side,
            classification, status, counterparty_id,
            fixed_price_value, reference, premium_discount,
            settlement_date, prompt_date, trade_date,
            source_type, source_id, notes, created_by,
            created_at, updated_at, deleted_at
        )
        SELECT
            h.id,
            h.commodity,
            h.tons,
            CAST(CASE WHEN h.direction = 'buy' THEN 'buy' ELSE 'sell' END AS hedge_leg_side),
            CAST(CASE WHEN h.direction = 'buy' THEN 'sell' ELSE 'buy' END AS hedge_leg_side),
            CAST(CASE WHEN h.direction = 'buy' THEN 'long' ELSE 'short' END AS hedge_classification),
            CAST(CASE
                WHEN h.status = 'active' THEN 'active'
                WHEN h.status = 'partially_settled' THEN 'partially_settled'
                WHEN h.status = 'settled' THEN 'settled'
                WHEN h.status = 'cancelled' THEN 'cancelled'
                ELSE 'active'
            END AS hedge_contract_status),
            CAST(h.counterparty_id AS VARCHAR(100)),
            h.price_per_ton,
            h.reference,
            h.premium_discount,
            h.settlement_date,
            h.prompt_date,
            h.trade_date,
            CAST(h.source_type AS VARCHAR(20)),
            h.source_id,
            h.notes,
            h.created_by,
            h.created_at,
            h.updated_at,
            h.deleted_at
        FROM hedges h
        WHERE h.contract_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM hedge_contracts hc WHERE hc.id = h.id
          )
    """)

    # ------------------------------------------------------------------
    # 5. Drop hedges table (now redundant)
    # ------------------------------------------------------------------
    op.drop_table("hedges")


def downgrade() -> None:
    # ------------------------------------------------------------------
    # Recreate hedges table (minimal structure for rollback)
    # ------------------------------------------------------------------
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    hedge_direction = sa.Enum("buy", "sell", name="hedge_direction")
    hedge_status = sa.Enum(
        "active", "partially_settled", "settled", "cancelled", name="hedge_status"
    )
    hedge_source_type = sa.Enum("rfq_award", "manual", "auto", name="hedge_source_type")

    op.create_table(
        "hedges",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("reference", sa.String(50), nullable=False, unique=True),
        sa.Column(
            "counterparty_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("counterparties.id"),
            nullable=False,
        ),
        sa.Column("commodity", sa.String(20), nullable=False),
        sa.Column("direction", hedge_direction, nullable=False),
        sa.Column("tons", sa.Numeric(15, 3), nullable=False),
        sa.Column("price_per_ton", sa.Numeric(15, 2), nullable=False),
        sa.Column(
            "premium_discount", sa.Numeric(15, 2), nullable=False, server_default="0"
        ),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("prompt_date", sa.Date(), nullable=True),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("status", hedge_status, nullable=False, server_default="active"),
        sa.Column("source_type", hedge_source_type, nullable=False),
        sa.Column("source_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "contract_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("hedge_contracts.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------
    # Remove new columns from hedge_contracts
    # ------------------------------------------------------------------
    cols_to_drop = [
        "reference",
        "premium_discount",
        "settlement_date",
        "prompt_date",
        "trade_date",
        "source_type",
        "source_id",
        "notes",
        "created_by",
        "updated_at",
    ]
    for col_name in cols_to_drop:
        op.drop_column("hedge_contracts", col_name)

    # Shrink counterparty_id back to VARCHAR(64)
    if is_pg:
        op.alter_column(
            "hedge_contracts",
            "counterparty_id",
            existing_type=sa.String(100),
            type_=sa.String(64),
            existing_nullable=True,
        )

    # Note: partially_settled enum value cannot be removed from PostgreSQL
    # enum types. This is a known limitation of ALTER TYPE ... DROP VALUE.
