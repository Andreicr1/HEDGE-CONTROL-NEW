# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Hedge Control Platform** — institutional commodity hedging system for LME Aluminium. Python 3.11 FastAPI backend + SAP UI5 1.136 frontend.

**Core design principles (from `docs/systemconstitucion.md`):**
- Correctness over convenience — no fallback silences or implicit inference
- Determinism — reproducible rankings, exposures, valuations
- Auditability — every mutation creates HMAC-SHA256 signed audit events
- Hard-fail — missing/ambiguous data blocks execution; never best-effort

---

## Running the Stack

### Backend

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Auth disabled in dev:** leave `JWT_ISSUER` unset — all requests get full `[trader, risk_manager, auditor]` roles automatically.

**Key env vars:**
- `DATABASE_URL` — required (`sqlite:///./test.db` for local, `postgresql+psycopg://...` for prod)
- `JWT_ISSUER`, `JWT_AUDIENCE`, `JWKS_URL` — JWT auth (omit for dev)
- `AUDIT_SIGNING_KEY` — HMAC-SHA256 key for audit event signatures
- `RATE_LIMIT_MUTATION` / `RATE_LIMIT_READ` / `RATE_LIMIT_SCRAPING` — defaults: 30/min, 60/min, 5/min
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` — LLM (GPT-4o-mini)
- `WHATSAPP_API_URL`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` — WhatsApp Cloud API

### Frontend

```bash
cd frontend
npm install
fiori run --open "test/flpSandbox.html?sap-ui-xx-viewCache=false#app-tile"
# or: npm run start-noflp
```

Frontend proxies all `/api/*` calls to `http://localhost:8000` via `frontend/ui5.yaml`.

### Full Stack (Docker)

```bash
docker-compose up
# PostgreSQL: 5432, Backend: 8000, Frontend: 8080
```

---

## Tests

```bash
cd backend
pytest -v
pytest tests/test_e2e_full_lifecycle.py -v        # lifecycle: SO→RFQ→Award→Contract→P&L
pytest tests/test_auth.py -v                      # JWT/role isolation
pytest --cov=app --cov-report=term-missing        # coverage
```

390+ tests covering: e2e lifecycle, RFQ state machine, exposure/MTM/P&L/cashflow calculations, audit HMAC, rate-limiting, cursor pagination, multi-commodity (6 LME metals).

---

## Architecture

### Backend (`backend/app/`)

```
api/routes/       17 thin route files — call services, enforce auth/rate-limit
services/         29 files — all business logic lives here
models/           16 SQLAlchemy 2.0 models (UUID PKs, soft-delete via deleted_at)
schemas/          19 Pydantic v2 schemas (strict, with max_length)
core/             auth.py, database.py, logging.py, rate_limit.py, pagination.py, metrics.py
tasks/            APScheduler jobs (Westmetall price ingest, RFQ timeout)
```

**Key services:**
- `rfq_service.py` + `rfq_orchestrator.py` — RFQ state machine
- `deal_engine.py` — SO → PO → Hedge aggregation
- `exposure_service.py` / `exposure_engine.py` — commercial + global exposure snapshots
- `finance_pipeline_service.py` — 6-stage daily pipeline
- `llm_agent.py` — Azure OpenAI quote parsing from WhatsApp text
- `audit_trail_service.py` — HMAC-SHA256 signed event log
- `lme_calendar.py` — LME holiday schedule (used in pricing/RFQ)

**Auth pattern:**
```python
# Any authenticated user
def get_entity(user: dict = Depends(get_current_user)): ...

# Role-enforced
def create_order(_: None = Depends(require_any_role("trader", "risk_manager"))): ...
```

**Pagination:** cursor-based on all list endpoints. `GET /orders/?cursor=<uuid>&limit=50`

**Migrations:** `cd backend && alembic revision --autogenerate -m "description"` → `alembic upgrade head`

### Frontend (`frontend/webapp/`)

SAP UI5 Flexible Column Layout (FCL) app. All economic logic lives in the backend — the frontend is a pure presenter.

```
controller/   30 controllers — all extend BaseController
view/         XML views (declarative UI, data binding via JSONModel)
service/      18 service files — thin HTTP wrappers around apiClient.js
fragment/     Reusable XML fragments (EmptyState, ConfirmDialog, KpiCard)
i18n/         i18n.properties (pt_BR default)
css/style.css SAP design tokens only (--sapPositiveColor etc.) — no hex values
```

**BaseController key methods** (inherited by all controllers):
- `initViewModel(name, data)` / `getViewModel()` — view-scoped JSONModel
- `loadData(fn, '/property')` — async load with busy indicator + error handling
- `loadParallel([fn1, fn2])` — Promise.all with 401→redirect, 403/429 logging
- `setLayout(layoutType)` — FCL layout transitions
- `getI18nText(key, [args])` — localization
- `_isValidId(sId)` — UUID v4 or numeric route param validation
- `showConfirm(message)` → `Promise<boolean>` — confirmation dialog

**Controller pattern:**
```javascript
// Every detail controller must implement onExit to detach route listeners
onInit: function () {
  this.getRouter().getRoute("myRoute").attachPatternMatched(this._onRouteMatched, this);
},
onExit: function () {
  this.getRouter().getRoute("myRoute").detachPatternMatched(this._onRouteMatched, this);
},
_onRouteMatched: function (oEvent) {
  var sId = oEvent.getParameter("arguments").myId;
  if (!this._isValidId(sId)) { this.getRouter().navTo("notFound"); return; }
  // load data...
},
```

**Service pattern:**
```javascript
// All services use apiClient.js — never call fetch() directly in services
return apiClient.getJson("/orders/count");
return apiClient.post("/orders/", oPayload);
```

**sap.viz (charts):** Lazy-loaded (`"lazy": true` in manifest). Never set `uiConfig` as an XML attribute — UI5 parses `{...}` as a binding expression. Use `setVizProperties()` programmatically instead.

---

## Economic Model

```
Sales Order (buy side)   → Commercial Active Exposure
Purchase Order (sell)    → Commercial Passive Exposure
Net Commercial Exposure  = Active − Passive

Hedge Short (unlinked)   → Global Active Exposure
Hedge Long (unlinked)    → Global Passive Exposure
Global Net Exposure      = primary risk KPI
```

**Valuation rules:**
- MTM uses D-1 Westmetall Cash Settlement price — no fallback, hard-fail if missing
- P&L = Realized (cashflow ledger entries) + Unrealized (MTM delta)
- Cashflow: 4 views — Analytic, Baseline, Ledger, What-If projection
- Snapshots are append-only and idempotent (same inputs → same snapshot)

**Hedge classification (deterministic):**
- Fixed Buy leg → Hedge Long
- Fixed Sell leg → Hedge Short

**RFQ lifecycle:** `CREATED → SENT (WhatsApp) → QUOTED (LLM parse) → AWARDED → CLOSED`

---

## Key Docs

- `docs/systemconstitucion.md` — canonical economic rules; read before changing any valuation logic
- `docs/GAP_ANALYSIS_LEGACY_VS_NEW.md` — comparison with legacy system
- `docs/solutions/` — documented solutions to past problems (searchable by tag)
- `ROADMAP_V2.md` — planned phases 6–12 (async SQLAlchemy, frontend container, E2E tests)

---

## Deployment

**Probes:** `GET /health` (liveness), `GET /ready` (readiness — checks DB + JWKS)
**Metrics:** `GET /metrics` (Prometheus)
**Target:** Azure Container Apps — configs in `deploy/aca/`
**Production server:** Gunicorn + UvicornWorker, 2 workers, port 8000
