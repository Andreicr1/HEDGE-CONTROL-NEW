# Phase 1 — Step 3 Execution Report

## Scope
Hedge contracts persistence and canonical classification only. No exposure reduction or linkage.

## Contract Schema
- commodity (string)
- quantity_mt (float, > 0)
- legs (exactly two: one fixed, one variable)
- fixed_leg_side (buy/sell)
- variable_leg_side (buy/sell)
- classification (long/short)

## Classification Rule
- Fixed BUY leg → LONG
- Fixed SELL leg → SHORT

## Validation Rules
- Exactly two legs required
- Exactly one fixed leg and one variable leg required
- quantity_mt must be > 0

## Explicit Exclusions
- No exposure reduction
- No linkage to orders
- No RFQ logic
- No valuation, MTM, CashFlow
- No global exposure
- No netting or aggregation
- No update or delete endpoints (append-only)

## Confirmation
- Exposure endpoints untouched and unaffected.

## Implemented
- SQLAlchemy HedgeContract model and enums
- Alembic migration for hedge_contracts table
- POST /contracts/hedge
- GET /contracts/hedge/{id}
- Deterministic classification logic
- Mandatory tests covering validation and classification

## Tests / Gate Evidence
- Not run (pytest not executed in this step)
