# Phase 3 — Step 3 Execution Report

## Scope
Awards, synchronous Hedge Contract creation, and Quote lifecycle user actions (Reject / Refresh / Award) with strictly governed RFQ state transitions and evidence persistence.

## Award Semantics (Binding)
- Award creates Hedge Contract(s) immediately and synchronously.
- Contract terms derived exclusively from:
  - the winning RFQ (trade RFQ)
  - the winning Quote (FIXED price only)
- No intermediate “award-only” entity exists.

## Award Cardinality (Binding)
- Single-trade RFQ (non-SPREAD): exactly one counterparty is awarded (rank 1).
- Multi-trade RFQ (SPREAD): one awarded counterparty produces one contract per referenced trade RFQ (buy_trade + sell_trade), fully covering each trade RFQ quantity.

## User Actions (Binding)
- Reject (Recusar):
  - RFQ remains economically empty; RFQ transitions QUOTED → CLOSED with evidence.
- Refresh (Atualizar):
  - Persists standardized refresh invitation messages to prior recipients.
  - RFQ state remains QUOTED; new quotes may be submitted; ranking recomputed deterministically on read.
- Award / Contract (Contratar):
  - Awards top-ranked quote(s), creates contract(s), applies linkage (commercial hedges), and closes RFQ.

## RFQ State Transitions (Binding)
Implemented exactly as governed for Step 3:
- QUOTED → AWARDED (user award action)
  - Evidence persisted:
    - winning_quote_id(s)
    - winning_counterparty_id(s)
    - ranking_snapshot
    - award_timestamp
    - user_id
- QUOTED → CLOSED (user reject action)
  - Evidence: reason=USER_REJECTED, timestamp, user_id
- AWARDED → CLOSED (contract creation completed)
  - Evidence: created_contract_id(s), timestamp

## Exposure Interaction (Binding)
- COMMERCIAL_HEDGE awards create hedge_order_linkages immediately for the awarded contract(s), thereby reducing commercial exposure via existing linkage-derived exposure rules.
- No new exposure recomputation methodology added.

## Implemented
- RFQ state enum extended: AWARDED, CLOSED.
- RFQ state event evidence extended to persist award/reject/close evidence fields.
- Hedge contract extended to record award-derived terms (rfq_id, rfq_quote_id, counterparty_id, fixed_price_value/unit, float_pricing_convention).
- Endpoints added:
  - POST `/rfqs/{rfq_id}/actions/reject`
  - POST `/rfqs/{rfq_id}/actions/refresh`
  - POST `/rfqs/{rfq_id}/actions/award`
  - GET `/rfqs/{rfq_id}/trade-ranking` (single-trade deterministic ranking)

## Explicit Exclusions (Confirmed)
- No MTM calculation
- No CashFlow generation
- No FX conversion (USD → BRL)
- No netting or optimization logic
- No incremental or cached exposure
- No repricing logic beyond quote refresh messaging persistence

## Files Added
- PHASE_3_STEP_3_EXECUTION_REPORT.md
- backend/alembic/versions/007_phase3_step3_award_and_contract_fields.py
- backend/tests/test_rfqs_step3.py

## Files Modified
- backend/app/api/routes/rfqs.py
- backend/app/models/contracts.py
- backend/app/models/rfqs.py
- backend/app/schemas/contracts.py
- backend/app/schemas/rfq.py
- backend/app/schemas/__init__.py
- backend/tests/test_contracts_hedge.py

## Tests / Gate Evidence
- Executed: `python -m pytest -q` (38 passed)

