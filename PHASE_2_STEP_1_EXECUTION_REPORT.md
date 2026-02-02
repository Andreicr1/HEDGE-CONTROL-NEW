# Phase 2 — Step 1 Execution Report

## Scope
Contract–Order linkage persistence and validation only. No exposure reduction.

## Linkage Model
- hedge_order_linkages
  - id (UUID)
  - order_id (UUID, FK orders.id)
  - contract_id (UUID, FK hedge_contracts.id)
  - quantity_mt (float, > 0)
  - created_at (timestamp)

## Validation Rules
- quantity_mt must be > 0
- Sum(linkages per order) <= order.quantity_mt
- Sum(linkages per contract) <= contract.quantity_mt
- Missing order or contract hard-fails

## Conservation Proof
- On insert, system recomputes total linked quantity by order and contract and rejects any linkage exceeding limits.

## Explicit Exclusions
- No exposure reduction
- No netting or aggregation
- No RFQ logic
- No valuation, MTM, CashFlow
- No exposure endpoint mutation

## Confirmation
- Exposure endpoints remain unchanged and unaffected.

## Implemented
- SQLAlchemy linkage model
- Alembic migration for hedge_order_linkages
- POST /linkages
- GET /linkages/{id}
- Mandatory tests for linkage constraints

## Tests / Gate Evidence
- Not run (pytest not executed in this step)
