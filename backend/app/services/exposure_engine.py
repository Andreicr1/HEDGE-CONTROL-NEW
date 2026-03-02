"""Exposure Engine service — reconciliation, net exposure, hedge tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.exposure import (
    Exposure,
    ExposureDirection,
    ExposureSourceType,
    ExposureStatus,
    HedgeTask,
    HedgeTaskAction,
    HedgeTaskStatus,
)
from app.models.orders import Order, OrderType


class ExposureEngineService:
    """Stateless service for the Exposure Engine."""

    # ------------------------------------------------------------------
    # reconcile_from_orders
    # ------------------------------------------------------------------

    @staticmethod
    def reconcile_from_orders(session: Session) -> dict:
        """Scan all active Orders and create / update Exposures.

        Returns a dict with ``created`` and ``updated`` counts.
        """
        created = 0
        updated = 0

        orders = session.query(Order).all()
        for order in orders:
            # Map order type → exposure direction / source_type
            if order.order_type == OrderType.purchase:
                direction = ExposureDirection.long
                source_type = ExposureSourceType.purchase_order
            else:
                direction = ExposureDirection.short
                source_type = ExposureSourceType.sales_order

            # Check if exposure already exists for this order
            existing = (
                session.query(Exposure)
                .filter(
                    Exposure.source_id == order.id,
                    Exposure.is_deleted == False,  # noqa: E712
                )
                .first()
            )

            if existing:
                # Update tons if order quantity changed
                if float(existing.original_tons) != float(order.quantity_mt):
                    existing.original_tons = order.quantity_mt
                    existing.open_tons = order.quantity_mt
                    updated += 1
            else:
                exposure = Exposure(
                    commodity="ALUMINUM",  # default commodity
                    direction=direction,
                    source_type=source_type,
                    source_id=order.id,
                    original_tons=order.quantity_mt,
                    open_tons=order.quantity_mt,
                    price_per_ton=order.avg_entry_price,
                    status=ExposureStatus.open,
                )
                session.add(exposure)
                created += 1

        session.commit()
        return {
            "created": created,
            "updated": updated,
            "message": "Reconciliation completed",
        }

    # ------------------------------------------------------------------
    # compute_net_exposure
    # ------------------------------------------------------------------

    @staticmethod
    def compute_net_exposure(
        session: Session, commodity: str | None = None
    ) -> list[dict]:
        """Compute net (long - short) exposure per commodity.

        If *commodity* is given, filter to that commodity only.
        """
        q = session.query(
            Exposure.commodity,
            Exposure.direction,
            func.coalesce(func.sum(Exposure.open_tons), 0).label("total_tons"),
        ).filter(
            Exposure.is_deleted == False,  # noqa: E712
            Exposure.status.in_([ExposureStatus.open, ExposureStatus.partially_hedged]),
        )

        if commodity:
            q = q.filter(Exposure.commodity == commodity)

        q = q.group_by(Exposure.commodity, Exposure.direction)
        rows = q.all()

        # Aggregate by commodity
        agg: dict[str, dict] = {}
        for row in rows:
            c = row.commodity
            if c not in agg:
                agg[c] = {
                    "commodity": c,
                    "long_tons": 0.0,
                    "short_tons": 0.0,
                    "net_tons": 0.0,
                }
            tons = float(row.total_tons)
            if row.direction == ExposureDirection.long:
                agg[c]["long_tons"] += tons
            else:
                agg[c]["short_tons"] += tons

        for v in agg.values():
            v["net_tons"] = v["long_tons"] - v["short_tons"]

        return list(agg.values())

    # ------------------------------------------------------------------
    # create_hedge_tasks
    # ------------------------------------------------------------------

    @staticmethod
    def create_hedge_tasks(session: Session) -> int:
        """For open exposures, create pending HedgeTasks.

        Returns count of tasks created.
        """
        open_exposures = (
            session.query(Exposure)
            .filter(
                Exposure.is_deleted == False,  # noqa: E712
                Exposure.status == ExposureStatus.open,
                Exposure.open_tons > 0,
            )
            .all()
        )

        count = 0
        for exp in open_exposures:
            # Check if a pending task already exists for this exposure
            existing_task = (
                session.query(HedgeTask)
                .filter(
                    HedgeTask.exposure_id == exp.id,
                    HedgeTask.status == HedgeTaskStatus.pending,
                )
                .first()
            )
            if existing_task:
                continue

            task = HedgeTask(
                exposure_id=exp.id,
                recommended_tons=exp.open_tons,
                recommended_action=HedgeTaskAction.hedge_new,
                status=HedgeTaskStatus.pending,
            )
            session.add(task)
            count += 1

        session.commit()
        return count

    # ------------------------------------------------------------------
    # cancel_stale_tasks
    # ------------------------------------------------------------------

    @staticmethod
    def cancel_stale_tasks(session: Session) -> int:
        """Cancel pending tasks whose exposures are fully hedged or cancelled.

        Returns count of tasks cancelled.
        """
        stale_tasks = (
            session.query(HedgeTask)
            .join(Exposure, HedgeTask.exposure_id == Exposure.id)
            .filter(
                HedgeTask.status == HedgeTaskStatus.pending,
                Exposure.status.in_(
                    [ExposureStatus.fully_hedged, ExposureStatus.cancelled]
                ),
            )
            .all()
        )

        count = 0
        for task in stale_tasks:
            task.status = HedgeTaskStatus.cancelled
            count += 1

        session.commit()
        return count
