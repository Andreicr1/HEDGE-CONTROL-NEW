# Phase 11 — Performance & Stress Validation

## Prerequisites
- Backend running (e.g. `uvicorn app.main:app --reload`).
- Environment variables for scenario IDs:
  - `LOCUST_LEDGER_CONTRACT_ID`
  - `LOCUST_WHATIF_ORDER_ID`
  - `LOCUST_WHATIF_CONTRACT_ID`

## Scenarios
- **Scenario A**: GET `/cashflow/ledger/hedge-contracts/{contract_id}` (10k entries).
- **Scenario B**: POST `/scenario/what-if/run` with 1k deltas.

## Run Locust
```
cd locust
locust -f locustfile.py --host http://localhost:8000
```

## Success Criteria
- Scenario A: p95 latency < 500 ms.
- Scenario B: completes < 5 s.