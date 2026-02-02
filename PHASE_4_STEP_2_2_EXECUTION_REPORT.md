# Phase 4 — Step 2.2 Execution Report

## Scope
MTM calculation for active hedge contracts using Cash Settlement D-1, plus snapshot persistence (append-only, idempotent, immutable evidence).

## Implemented
- MTM snapshots persistence
  - `mtm_snapshots` table with unique constraint `(object_type, object_id, as_of_date)`
  - Fields: `mtm_value`, `price_d1`, `entry_price`, `quantity_mt`, `correlation_id`, timestamps
  - Object types: `hedge_contract`, `order` (order snapshots are not yet supported by services/routes in this step)
- Hedge contract status gate
  - Added `status` to hedge contracts with allowed values: `active`, `cancelled`, `settled`
  - MTM is computed only when `status == active`
- MTM computation (contracts)
  - Uses `get_cash_settlement_price_d1()` (calendar D-1, UTC dates, no fallback; missing price hard-fails HTTP 424)
  - Formula: `mtm_value = quantity_mt * (price_d1 - entry_price)`
  - `entry_price` is the contract `fixed_price_value` (hard-fail if missing)
- Snapshot creation service
  - Idempotent: if snapshot exists and values match → returns existing
  - Conflict: if snapshot exists and values differ → HTTP 409
- API routes
  - `GET /mtm/hedge-contracts/{contract_id}?as_of_date=YYYY-MM-DD`
  - `POST /mtm/snapshots`
  - `GET /mtm/snapshots?object_type=...&object_id=...&as_of_date=...`

## Explicit Exclusions (Confirmed)
- No MTM for orders (reserved for Phase 4 — Step 2.3)
- No bulk snapshot creation
- No FX conversion
- No holiday calendar logic

## Files Added
- `backend/app/models/mtm.py`
- `backend/app/schemas/mtm.py`
- `backend/app/services/mtm_contract_service.py`
- `backend/app/services/mtm_snapshot_service.py`
- `backend/app/api/routes/mtm.py`
- `backend/alembic/versions/009_phase4_step2_mtm_snapshots.py`
- `backend/alembic/versions/010_add_hedge_contract_status.py`
- `backend/tests/test_mtm_contract_service.py`
- `PHASE_4_STEP_2_2_EXECUTION_REPORT.md`

## Files Modified
- `backend/app/models/contracts.py`
- `backend/app/api/routes/contracts.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/contracts.py`
- `backend/app/schemas/__init__.py`
- `backend/app/api/routes/__init__.py`
- `backend/app/main.py`

## Tests / Gate Evidence
- Executed: `python -m pytest tests/test_mtm_contract_service.py -v` (5 passed)
- Executed: `python -m pytest -q` (49 passed)

