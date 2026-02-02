# Phase 4 — Step 3.2 Execution Report

## Scope
Persistent CashFlow Baseline snapshots for institutional record-keeping.
Snapshots are derived from the Analytic view and persisted with idempotency + conflict detection.

## Implemented
- Persistence
  - `cashflow_baseline_snapshots` table
  - Unique constraint on `as_of_date`
  - Stores:
    - `snapshot_data` (JSON)
    - `total_net_cashflow`
    - `correlation_id`
    - `created_at`
- Service
  - `create_cashflow_baseline_snapshot(db, as_of_date, correlation_id)`
    - Calls `compute_cashflow_analytic(db, as_of_date)`
    - Persists snapshot payload deterministically (canonicalized ordering)
    - Idempotent: if snapshot exists and matches → returns existing
    - Conflict: if snapshot exists and differs → HTTP 409
    - Propagates HTTP 424 if D-1 price missing
- API routes
  - `POST /cashflow/baseline/snapshots`
  - `GET /cashflow/baseline/snapshots?as_of_date=YYYY-MM-DD`

## Explicit Exclusions (Confirmed)
- No Ledger view
- No What-If view
- No P&L calculation (Phase 4 — Step 4)

## Files Added
- `backend/app/models/cashflow.py`
- `backend/app/services/cashflow_baseline_service.py`
- `backend/alembic/versions/012_phase4_step3_cashflow_baseline_snapshots.py`
- `backend/tests/test_cashflow_baseline_service.py`
- `PHASE_4_STEP_3_2_EXECUTION_REPORT.md`

## Files Modified
- `backend/app/models/__init__.py`
- `backend/app/schemas/cashflow.py`
- `backend/app/schemas/__init__.py`
- `backend/app/api/routes/cashflow.py`

## Tests / Gate Evidence
- Executed: `python -m pytest tests/test_cashflow_baseline_service.py -v` (4 passed)
- Executed: `python -m pytest -q` (63 passed)

