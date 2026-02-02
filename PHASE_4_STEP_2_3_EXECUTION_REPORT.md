# Phase 4 — Step 2.3 Execution Report

## Scope
MTM engine support for variable-price orders (AVG, AVGInter, C2R) using Cash Settlement D-1. Fixed-price orders are explicitly out of scope for this step.

## Governance Decisions Applied (Binding)
- Variable-order MTM only; fixed-price orders excluded.
- Quantity used for MTM is always full `order.quantity_mt` (no residual quantity concept in MTM).
- D-1 rule is calendar day in UTC; no fallback to business days; missing D-1 price hard-fails (HTTP 424).

## Implemented
- Order pricing fields (to support deterministic MTM eligibility)
  - `orders.pricing_convention` (nullable; eligible values: AVG, AVGInter, C2R)
  - `orders.avg_entry_price` (nullable, USD/MT)
  - Backward compatibility preserved: variable orders can still be created without these fields; MTM requires them.
- MTM computation for variable orders
  - Service: `compute_mtm_for_order(db, order_id, as_of_date)`
  - Eligibility:
    - `order.price_type == variable`
    - `pricing_convention ∈ {AVG, AVGInter, C2R}`
    - `avg_entry_price` present
  - Formula:
    - `mtm_value = quantity_mt * (price_d1 - avg_entry_price)`
  - Uses `get_cash_settlement_price_d1()` and hard-fails 424 on missing D-1 price.
- Snapshot support for orders
  - Reuses `mtm_snapshots` table (no new snapshot migration)
  - Same idempotency/conflict rules as hedge contracts:
    - existing snapshot with same values ⇒ return existing
    - existing snapshot with different values ⇒ HTTP 409
- API routes
  - Added: `GET /mtm/orders/{order_id}?as_of_date=YYYY-MM-DD`
  - Extended: `POST /mtm/snapshots` now supports `object_type=order`
  - Existing: `GET /mtm/snapshots` supports `object_type=order`

## Explicit Exclusions (Confirmed)
- Fixed-price orders MTM (explicitly excluded by governance for Step 2.3)
- Bulk snapshot creation
- CashFlow views (Phase 4 — Step 3)
- FX conversion

## Files Added
- `backend/app/services/mtm_order_service.py`
- `backend/alembic/versions/011_add_order_pricing_fields.py`
- `backend/tests/test_mtm_order_service.py`
- `PHASE_4_STEP_2_3_EXECUTION_REPORT.md`

## Files Modified
- `backend/app/models/orders.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/orders.py`
- `backend/app/api/routes/orders.py`
- `backend/app/services/mtm_snapshot_service.py`
- `backend/app/api/routes/mtm.py`

## Tests / Gate Evidence
- Executed: `python -m pytest tests/test_mtm_order_service.py -v` (6 passed)
- Executed: `python -m pytest -q` (55 passed)

