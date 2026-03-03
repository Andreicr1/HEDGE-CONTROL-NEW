"""Deal Engine service — CRUD + links + P&L snapshots (component 1.5).

P&L logic
---------
Physical P&L  = SO revenue − PO cost
  * Fixed-price orders  → qty × avg_entry_price
  * Variable-price orders → qty × settlement_price (market)

Financial P&L = hedge positions linked to the deal
  * Settled hedges (realized):
      sell → +tons × price_per_ton
      buy  → −tons × price_per_ton
  * Active hedges (MTM / unrealised):
      buy  → tons × (market_price − price_per_ton)
      sell → tons × (price_per_ton − market_price)

Total P&L = physical_revenue − physical_cost + hedge_realized + hedge_mtm
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid as _uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealLink, DealLinkedType, DealPNLSnapshot, DealStatus
from app.models.hedge import Hedge, HedgeDirection, HedgeStatus
from app.models.orders import Order, OrderType, PriceType

logger = logging.getLogger(__name__)

DEFAULT_COMMODITY_SYMBOL = "LME_AL"


def _generate_reference() -> str:
    """Generate a unique deal reference like D-XXXXXXXX."""
    return f"D-{_uuid.uuid4().hex[:8].upper()}"


def _compute_inputs_hash(
    deal_id: _uuid.UUID,
    snapshot_date: date,
    link_ids: list[_uuid.UUID],
) -> str:
    """SHA-256 hash that changes when the deal's links change."""
    data = json.dumps(
        {
            "deal_id": str(deal_id),
            "snapshot_date": str(snapshot_date),
            "links": sorted(str(lid) for lid in link_ids),
        },
        sort_keys=True,
    )
    return hashlib.sha256(data.encode()).hexdigest()


def _get_market_price(session: Session, commodity: str, as_of_date: date) -> float | None:
    """Try to fetch the D-1 settlement price; return None on failure."""
    try:
        from app.services.price_lookup_service import (
            get_cash_settlement_price_d1,
            resolve_symbol,
        )
        symbol = resolve_symbol(commodity)
        return float(get_cash_settlement_price_d1(session, symbol=symbol, as_of_date=as_of_date))
    except Exception:
        logger.debug("market_price_unavailable commodity=%s date=%s", commodity, as_of_date)
        return None


class DealEngineService:
    """Stateless service for Deal operations."""

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    @staticmethod
    def create_deal(session: Session, data: dict) -> Deal:
        """Create a deal and optionally add initial links."""
        links_data = data.pop("links", [])

        deal = Deal(
            reference=_generate_reference(),
            name=data["name"],
            commodity=data["commodity"],
            status=DealStatus.open,
        )
        session.add(deal)
        session.flush()

        # Add initial links
        for link_data in links_data:
            link = DealLink(
                deal_id=deal.id,
                linked_type=DealLinkedType(link_data["linked_type"]),
                linked_id=link_data["linked_id"],
            )
            session.add(link)

        session.flush()
        DealEngineService._recompute_tons(session, deal)
        session.commit()
        session.refresh(deal)
        return deal

    # ------------------------------------------------------------------
    # LINKS
    # ------------------------------------------------------------------

    @staticmethod
    def add_link(
        session: Session, deal_id: _uuid.UUID, linked_type: str, linked_id: _uuid.UUID
    ) -> DealLink:
        """Add a link to a deal."""
        deal = DealEngineService.get_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )

        # Check for duplicate
        existing = (
            session.query(DealLink)
            .filter(
                DealLink.deal_id == deal_id,
                DealLink.linked_type == DealLinkedType(linked_type),
                DealLink.linked_id == linked_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Link already exists",
            )

        link = DealLink(
            deal_id=deal_id,
            linked_type=DealLinkedType(linked_type),
            linked_id=linked_id,
        )
        session.add(link)
        session.flush()

        DealEngineService._recompute_tons(session, deal)
        session.commit()
        session.refresh(link)
        return link

    @staticmethod
    def remove_link(session: Session, deal_id: _uuid.UUID, link_id: _uuid.UUID) -> None:
        """Remove a link from a deal."""
        deal = DealEngineService.get_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )

        link = (
            session.query(DealLink)
            .filter(DealLink.id == link_id, DealLink.deal_id == deal_id)
            .first()
        )
        if not link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
            )

        session.delete(link)
        session.flush()

        DealEngineService._recompute_tons(session, deal)
        session.commit()

    # ------------------------------------------------------------------
    # P&L SNAPSHOT
    # ------------------------------------------------------------------

    @staticmethod
    def _order_value(
        order: Order, market_price: float | None,
    ) -> float:
        """Return the monetary value for one order (qty × effective price).

        Fixed-price orders always use ``avg_entry_price``.
        Variable-price orders prefer the market settlement price;
        fall back to ``avg_entry_price`` when market data is unavailable.
        """
        qty = float(order.quantity_mt)
        if order.price_type == PriceType.fixed:
            return qty * float(order.avg_entry_price or 0)
        if market_price is not None:
            return qty * market_price
        return qty * float(order.avg_entry_price or 0)

    @staticmethod
    def compute_deal_pnl(
        session: Session, deal_id: _uuid.UUID, snapshot_date: date
    ) -> DealPNLSnapshot:
        """Compute deal P&L and persist a snapshot.

        Idempotent: if the set of links hasn't changed for the same date the
        existing snapshot is returned.  When links change a fresh snapshot is
        created (different ``inputs_hash``).
        """
        deal = DealEngineService.get_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )

        links = session.query(DealLink).filter(DealLink.deal_id == deal_id).all()
        inputs_hash = _compute_inputs_hash(
            deal_id, snapshot_date, [lk.id for lk in links]
        )

        existing = (
            session.query(DealPNLSnapshot)
            .filter(DealPNLSnapshot.inputs_hash == inputs_hash)
            .first()
        )
        if existing:
            return existing

        market_price = _get_market_price(session, deal.commodity, snapshot_date)

        physical_revenue = 0.0
        physical_cost = 0.0
        hedge_pnl_realized = 0.0
        hedge_pnl_mtm = 0.0

        for link in links:
            # ── Physical side (orders) ──
            if link.linked_type == DealLinkedType.sales_order:
                order = session.get(Order, link.linked_id)
                if order:
                    physical_revenue += DealEngineService._order_value(
                        order, market_price
                    )

            elif link.linked_type == DealLinkedType.purchase_order:
                order = session.get(Order, link.linked_id)
                if order:
                    physical_cost += DealEngineService._order_value(
                        order, market_price
                    )

            # ── Financial side (hedges) ──
            elif link.linked_type == DealLinkedType.hedge:
                hedge = session.get(Hedge, link.linked_id)
                if not hedge:
                    continue

                tons = float(hedge.tons)
                price = float(hedge.price_per_ton)
                is_sell = hedge.direction == HedgeDirection.sell

                if hedge.status == HedgeStatus.settled:
                    if is_sell:
                        hedge_pnl_realized += tons * price
                    else:
                        hedge_pnl_realized -= tons * price
                else:
                    if market_price is not None:
                        if is_sell:
                            hedge_pnl_mtm += tons * (price - market_price)
                        else:
                            hedge_pnl_mtm += tons * (market_price - price)

        total_pnl = (
            physical_revenue - physical_cost + hedge_pnl_realized + hedge_pnl_mtm
        )

        snapshot = DealPNLSnapshot(
            deal_id=deal_id,
            snapshot_date=snapshot_date,
            physical_revenue=physical_revenue,
            physical_cost=physical_cost,
            hedge_pnl_realized=hedge_pnl_realized,
            hedge_pnl_mtm=hedge_pnl_mtm,
            total_pnl=total_pnl,
            inputs_hash=inputs_hash,
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return snapshot

    @staticmethod
    def get_pnl_history(session: Session, deal_id: _uuid.UUID) -> list[DealPNLSnapshot]:
        """Return P&L snapshot history for a deal."""
        deal = DealEngineService.get_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )
        return (
            session.query(DealPNLSnapshot)
            .filter(DealPNLSnapshot.deal_id == deal_id)
            .order_by(DealPNLSnapshot.snapshot_date.desc())
            .all()
        )

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    @staticmethod
    def update_deal_status(session: Session, deal_id: _uuid.UUID) -> Deal:
        """Update deal status based on hedge_ratio."""
        deal = DealEngineService.get_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )

        ratio = float(deal.hedge_ratio)
        if ratio <= 0:
            deal.status = DealStatus.open
        elif ratio < 1.0:
            deal.status = DealStatus.partially_hedged
        else:
            deal.status = DealStatus.fully_hedged

        session.commit()
        session.refresh(deal)
        return deal

    # ------------------------------------------------------------------
    # LIST / GET
    # ------------------------------------------------------------------

    @staticmethod
    def list_deals(
        session: Session,
        commodity: str | None = None,
        status_filter: str | None = None,
    ):
        """Return query for deals with filters."""
        q = session.query(Deal).filter(Deal.is_deleted == False)  # noqa: E712
        if commodity:
            q = q.filter(Deal.commodity == commodity)
        if status_filter:
            q = q.filter(Deal.status == DealStatus(status_filter))
        return q.order_by(Deal.created_at.desc())

    @staticmethod
    def get_by_id(session: Session, deal_id: _uuid.UUID) -> Deal | None:
        return (
            session.query(Deal)
            .filter(Deal.id == deal_id, Deal.is_deleted == False)  # noqa: E712
            .first()
        )

    @staticmethod
    def get_detail(session: Session, deal_id: _uuid.UUID) -> dict:
        """Get deal with links and latest PNL snapshot."""
        deal = DealEngineService.get_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )

        links = session.query(DealLink).filter(DealLink.deal_id == deal_id).all()
        latest_pnl = (
            session.query(DealPNLSnapshot)
            .filter(DealPNLSnapshot.deal_id == deal_id)
            .order_by(DealPNLSnapshot.created_at.desc())
            .first()
        )

        return {
            "id": deal.id,
            "reference": deal.reference,
            "name": deal.name,
            "commodity": deal.commodity,
            "status": deal.status,
            "total_physical_tons": deal.total_physical_tons,
            "total_hedge_tons": deal.total_hedge_tons,
            "hedge_ratio": deal.hedge_ratio,
            "created_at": deal.created_at,
            "updated_at": deal.updated_at,
            "is_deleted": deal.is_deleted,
            "links": links,
            "latest_pnl": latest_pnl,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _recompute_tons(session: Session, deal: Deal) -> None:
        """Recompute physical/hedge tons and ratio from links."""
        links = session.query(DealLink).filter(DealLink.deal_id == deal.id).all()

        physical_tons = 0.0
        hedge_tons = 0.0

        for link in links:
            if link.linked_type in (
                DealLinkedType.sales_order,
                DealLinkedType.purchase_order,
            ):
                order = session.query(Order).filter(Order.id == link.linked_id).first()
                if order:
                    physical_tons += float(order.quantity_mt)
            elif link.linked_type == DealLinkedType.hedge:
                hedge = session.query(Hedge).filter(Hedge.id == link.linked_id).first()
                if hedge:
                    hedge_tons += float(hedge.tons)

        deal.total_physical_tons = physical_tons
        deal.total_hedge_tons = hedge_tons
        deal.hedge_ratio = (hedge_tons / physical_tons) if physical_tons > 0 else 0

        # Auto-update status
        ratio = deal.hedge_ratio
        if ratio <= 0:
            deal.status = DealStatus.open
        elif ratio < 1.0:
            deal.status = DealStatus.partially_hedged
        else:
            deal.status = DealStatus.fully_hedged
