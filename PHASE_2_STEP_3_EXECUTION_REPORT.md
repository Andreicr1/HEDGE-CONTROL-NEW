# Phase 2 — Step 3 Execution Report

## Scope
Global exposure reduction derived from reduced commercial exposure and unlinked hedge quantities. Recomputed from scratch; no persistence.

## Reduction Formulas
Inputs:
- Reduced Commercial Active/Passive (orders minus linkages)
- Hedge Contracts (classification)
- Linkages (to compute unlinked hedge quantities)

Pre-reduction (audit):
- Pre Global Active = Pre Commercial Active + Σ(total hedge short)
- Pre Global Passive = Pre Commercial Passive + Σ(total hedge long)

Post-reduction:
- Unlinked Hedge Short = Σ(contract.quantity_mt − linked_qty_per_contract) where classification=short
- Unlinked Hedge Long = Σ(contract.quantity_mt − linked_qty_per_contract) where classification=long
- Global Active = Reduced Commercial Active + Unlinked Hedge Short
- Global Passive = Reduced Commercial Passive + Unlinked Hedge Long
- Global Net = Global Active − Global Passive

Reduction Applied:
- Reduction Active = Pre Global Active − Global Active
- Reduction Passive = Pre Global Passive − Global Passive

## Data Sources
- orders
- hedge_contracts
- hedge_order_linkages

## Audit Fields Returned
- pre_reduction_global_active_mt
- pre_reduction_global_passive_mt
- reduction_applied_active_mt
- reduction_applied_passive_mt
- global_active_mt
- global_passive_mt
- global_net_mt
- commercial_active_mt
- commercial_passive_mt
- hedge_long_mt
- hedge_short_mt
- calculation_timestamp
- entities_count_considered

## Explicit Exclusions
- No persistence of reduced global exposure
- No RFQ logic
- No valuation, MTM, CashFlow
- No incremental or cached computation
- No mutation of existing entities

## Confirmation
- Computation is recomputed from scratch on each request.
- Linked hedge quantities are excluded from global exposure.

## Tests / Gate Evidence
- Not run (pytest not executed in this step)
