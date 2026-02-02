# Phase 1 — Step 2 Execution Report

## Scope
Commercial exposure state derived exclusively from persisted Orders. Read-only endpoint.

## Formula Used
- Commercial Active Exposure = sum(quantity_mt) for variable-price Sales Orders (SO)
- Commercial Passive Exposure = sum(quantity_mt) for variable-price Purchase Orders (PO)
- Commercial Net Exposure = Active - Passive

## Tables Accessed
- orders

## Fields Used
- orders.order_type
- orders.price_type
- orders.quantity_mt
- orders.id (count)

## Explicit Exclusions
- Fixed-price orders excluded from exposure
- No hedge linkage
- No RFQ, valuation, cashflow, or global exposure logic
- No exposure persistence
- No incremental or cached computation

## Implemented
- GET /exposures/commercial endpoint with full recomputation per request
- Commercial exposure response schema
- Deterministic test suite for exposure rules

## Not Implemented
- Hedge contracts
- RFQ system
- Global exposure
- MTM or CashFlow
- Exposure persistence or CRUD

## Tests Added (Mandatory)
- Fixed-price orders do NOT affect exposure
- Variable-price orders DO affect exposure
- Sales and Purchase orders affect opposite sides
- Reordering inserts does NOT change exposure
- Empty orders returns zero exposure

## Tests / Gate Evidence
- Not run (pytest not executed in this step)
