# Phase 3 — Step 1 Execution Report

## Scope
RFQ definition and persistence only. No quotes, ranking, awards, or contract creation.

## RFQ Model
- rfq_number (server-generated RFQ-YYYY-######)
- intent (COMMERCIAL_HEDGE | GLOBAL_POSITION)
- commodity
- quantity_mt (> 0)
- delivery_window_start / delivery_window_end
- direction (BUY | SELL)
- order_id (required only for COMMERCIAL_HEDGE)
- commercial_active_mt
- commercial_passive_mt
- commercial_net_mt
- commercial_reduction_applied_mt (pre_active − post_active)
- exposure_snapshot_timestamp
- state (CREATED | SENT | QUOTED)

## Invitation Model
- rfq_id
- rfq_number
- recipient_id
- recipient_name
- channel
- message_body (mandatory)
- provider_message_id
- send_status (queued | sent | failed)
- sent_at
- idempotency_key

## State Machine (Step 1)
- CREATED → SENT when at least one invitation has send_status in {queued, sent}
- SENT → QUOTED is not allowed in Step 1
- Transition emits rfq_state_events record

## Validation Rules
- COMMERCIAL_HEDGE: order_id required, order must be variable-price
- COMMERCIAL_HEDGE: SO → SELL, PO → BUY
- COMMERCIAL_HEDGE: quantity_mt ≤ residual commercial_active_mt
- GLOBAL_POSITION: order_id forbidden
- quantity_mt > 0

## Data Sources
- orders
- hedge_order_linkages

## Explicit Exclusions
- No quote ranking
- No awards
- No contract creation
- No exposure mutation
- No RFQ listing or updates

## Confirmation
- RFQ creation does not mutate exposure endpoints.
- Exposure snapshot stored on RFQ is immutable.

## Implemented
- RFQ persistence with deterministic server-generated rfq_number
- RFQ invitation persistence as evidence
- RFQ state machine (CREATED/SENT)
- POST /rfqs and GET /rfqs/{id}
- Alembic migration for RFQ tables
- Mandatory tests for constraints

## Tests / Gate Evidence
- Not run (pytest not executed in this step)
