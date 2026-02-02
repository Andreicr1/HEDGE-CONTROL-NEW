# Phase 2 — Step 2 Execution Report

## Scope
Commercial exposure reduction based on hedge–order linkages. Recomputed from scratch. No persistence of reduced state.

## Reduction Formula
For each variable-price order:
Residual_Order_Exposure = order.quantity_mt − Σ(linked_qty_for_order)

Aggregations:
- Commercial Active Exposure = Σ(residual variable SO orders)
- Commercial Passive Exposure = Σ(residual variable PO orders)
- Commercial Net Exposure = Active − Passive

## Tables Used
- orders
- hedge_order_linkages

## Audit Fields Returned
- pre_reduction_commercial_active_mt
- pre_reduction_commercial_passive_mt
- reduction_applied_active_mt
- reduction_applied_passive_mt
- commercial_active_mt
- commercial_passive_mt
- commercial_net_mt
- calculation_timestamp
- order_count_considered

## Explicit Exclusions
- No global exposure reduction
- No RFQ logic
- No valuation, MTM, CashFlow
- No persistence of reduced exposure
- No incremental or cached computation

## Confirmation
- Computation recomputed from scratch on each request.
- Orders and linkages remain immutable.

## Implemented
- Commercial exposure endpoint now applies linkage reduction
- Residual non-negative hard-fail
- Mandatory tests for reduction rules

## Tests / Gate Evidence
- Not run (pytest not executed in this step)
