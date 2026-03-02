"""Deal Engine service — CRUD + links + P&L snapshots (component 1.5)."""

from __future__ import annotations

import hashlib
import json
import uuid as _uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealLink, DealLinkedType, DealPNLSnapshot, DealStatus
from app.models.hedge import Hedge
from app.models.orders import Order, OrderType


def _generate_reference() -> str:
    """Generate a unique deal reference like D-XXXXXXXX."""
    return f"D-{_uuid.uuid4().hex[:8].upper()}"


def _compute_inputs_hash(deal_id: _uuid.UUID, snapshot_date: date) -> str:
    """SHA-256 hash for idempotency check."""
    data = json.dumps(
        {"deal_id": str(deal_id), "snapshot_date": str(snapshot_date)}, sort_keys=True
    )
    return hashlib.sha256(data.encode()).hexdigest()


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
    def compute_deal_pnl(
        session: Session, deal_id: _uuid.UUID, snapshot_date: date
    ) -> DealPNLSnapshot:
        """Compute deal P&L and create a snapshot. Idempotent via inputs_hash."""
        deal = DealEngineService.get_by_id(session, deal_id)
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found"
            )

        inputs_hash = _compute_inputs_hash(deal_id, snapshot_date)

        # Check for existing snapshot with same hash (idempotency)
        existing = (
            session.query(DealPNLSnapshot)
            .filter(DealPNLSnapshot.inputs_hash == inputs_hash)
            .first()
        )
        if existing:
            return existing

        # Gather linked items
        links = session.query(DealLink).filter(DealLink.deal_id == deal_id).all()

        physical_revenue = 0.0
        physical_cost = 0.0
        hedge_pnl_realized = 0.0

        for link in links:
            if link.linked_type == DealLinkedType.sales_order:
                order = session.query(Order).filter(Order.id == link.linked_id).first()
                if order:
                    physical_revenue += float(order.quantity_mt) * float(
                        order.avg_entry_price or 0
                    )
            elif link.linked_type == DealLinkedType.purchase_order:
                order = session.query(Order).filter(Order.id == link.linked_id).first()
                if order:
                    physical_cost += float(order.quantity_mt) * float(
                        order.avg_entry_price or 0
                    )
            elif link.linked_type == DealLinkedType.hedge:
                hedge = session.query(Hedge).filter(Hedge.id == link.linked_id).first()
                if hedge:
                    # Simplified: hedge P&L = tons * premium_discount
                    hedge_pnl_realized += float(hedge.tons) * float(
                        hedge.premium_discount or 0
                    )

        total_pnl = physical_revenue - physical_cost + hedge_pnl_realized

        snapshot = DealPNLSnapshot(
            deal_id=deal_id,
            snapshot_date=snapshot_date,
            physical_revenue=physical_revenue,
            physical_cost=physical_cost,
            hedge_pnl_realized=hedge_pnl_realized,
            hedge_pnl_mtm=0,  # simplified — would come from MTM service
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
