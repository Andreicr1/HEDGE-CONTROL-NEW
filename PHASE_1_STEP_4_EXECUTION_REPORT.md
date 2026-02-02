# Phase 1 — Step 4 Execution Report

## Scope
Global Exposure read-only aggregation from Commercial Exposure and unlinked Hedge Contracts.

## Data Sources Used
- orders (commercial exposure)
- hedge_contracts (classification and quantity)

## Formula Applied
- Commercial Active = sum(variable SO quantity)
- Commercial Passive = sum(variable PO quantity)
- Hedge Short = sum(hedge_contracts.quantity_mt where classification = short)
- Hedge Long = sum(hedge_contracts.quantity_mt where classification = long)
- Global Active = Commercial Active + Hedge Short
- Global Passive = Commercial Passive + Hedge Long
- Global Net = Global Active - Global Passive

## Explicit Exclusions
- No linkage between contracts and orders
- No exposure reduction
- No RFQ logic
- No valuation, MTM, CashFlow
- No global exposure persistence
- No incremental or cached computation

## Confirmation
- Recomputed from scratch per request.
- Exposure endpoints remain read-only.

## Implemented
- GET /exposures/global endpoint
- Global exposure response schema
- Deterministic tests covering required rules

## Tests / Gate Evidence
- Not run (pytest not executed in this step)
