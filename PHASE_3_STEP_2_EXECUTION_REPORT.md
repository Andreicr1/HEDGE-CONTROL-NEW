# Phase 3 — Step 2 Execution Report

## Scope
Deterministic Quote intake and deterministic Spread-based ranking (inter-trade), per finalized governance decision.

## Governance Implemented (Binding)
- Quote persists FIXED leg price only:
  - fixed_price_value
  - fixed_price_unit (USD/MT syntactic equivalents only; no conversions)
  - float_pricing_convention (avg | avginter | c2r)
  - received_at
- Spread ranking is inter-trade:
  - spread_value = fixed_price(sell_trade.rfq) − fixed_price(buy_trade.rfq)
- Ranking direction:
  - Descending by spread_value (larger spread ranks better)
- Eligibility:
  - Incomplete quotes rejected at intake
  - Absence of quote from a counterparty is ignored
  - Latest-per-counterparty by received_at is used per RFQ
  - If zero eligible counterparties exist, ranking returns failure payload with no ordering
- Comparability (hard constraints):
  - USD-only, unit of mass only
  - USD/MT ≡ USDMT ≡ USD-MT (case-insensitive; normalize “/” and “-”; no conversions)
  - Any non-canonical unit causes ranking failure payload
- No ties allowed:
  - If two or more counterparties have equal spread_value, ranking returns failure payload with no ordering
- RFQ state transition (Step 2 only):
  - SENT → QUOTED triggered by persistence of the first complete quote
  - Evidence persisted: trigger, triggering_quote_id, triggering_counterparty_id, event_timestamp
- Ranking failures:
  - Successful HTTP response with explicit failure metadata, no ordering

## Implemented
- RFQ intent extended:
  - Added SPREAD intent with buy_trade_id / sell_trade_id references (trade RFQs are existing RFQs; SPREAD RFQ references two RFQ ids)
- Quote intake:
  - POST /rfqs/{rfq_id}/quotes (append-only)
  - SPREAD RFQs cannot receive quotes
  - RFQ must be in state SENT or QUOTED to receive quotes
  - First persisted quote transitions RFQ from SENT → QUOTED and emits rfq_state_events evidence
- Spread ranking:
  - GET /rfqs/{rfq_id}/ranking computes ranking only when intent=SPREAD
  - No persistence, no caching, recomputed from scratch per request

## Explicit Exclusions (Confirmed)
- No awards
- No contract creation
- No exposure mutation or recalculation beyond reading authoritative exposures for snapshot at RFQ creation
- No RFQ state transitions beyond SENT → QUOTED
- No FX logic or BRL conversion
- No MTM or CashFlow logic
- No incremental or cached ranking

## Files Added
- PHASE_3_STEP_2_EXECUTION_REPORT.md
- backend/alembic/versions/006_update_rfqs_for_spread_ranking.py

## Files Modified
- backend/app/api/routes/rfqs.py
- backend/app/api/routes/exposures.py
- backend/app/models/rfqs.py
- backend/app/models/quotes.py
- backend/app/schemas/rfq.py
- backend/app/schemas/__init__.py
- backend/tests/test_rfqs_step1.py
- backend/tests/test_rfqs_step2.py

## Tests / Gate Evidence
- Executed: `python -m pytest -q` (34 passed)

