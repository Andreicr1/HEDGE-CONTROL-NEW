---
status: done
priority: p1
issue_id: "002"
tags: [ui5, home, kpi, services, error-handling]
dependencies: []
---

# Create PnlService + CashflowService and Populate Missing KPI Tiles

## Problem Statement

The Home dashboard declares 6 KPI tiles in the view. The controller only populates 4 of them (`kpiExposureValue`, `kpiOrdersCount`, `kpiContractsCount`, `kpiRfqsCount`). The **`kpiPnlValue` and `kpiCashflowValue` tiles permanently display "–"** because the backing services (`PnlService.js`, `CashflowService.js`) do not exist in `webapp/service/`. Additionally, `_loadKpis` has no `.catch()` handler — if any of the 4 existing API calls reject, all KPI tiles silently remain at "–" with no user notification.

## Findings

- `webapp/controller/Home.controller.js:33-47`: `_loadKpis()` sets only 4 model properties; `kpiPnlValue` and `kpiCashflowValue` are initialized in `onInit` but never updated
- `webapp/service/` directory contains: `ContractsService.js`, `CounterpartysService.js`, `ExposuresService.js`, `OrdersService.js`, `RfqsService.js` — **no PnlService or CashflowService**
- `webapp/view/Home.view.xml:59-82`: tiles for `homeKpiPnl` and `homeKpiCashflow` are fully rendered in the view, binding to `{viewModel>/kpiPnlValue}` and `{viewModel>/kpiCashflowValue}`
- Every other controller (`Contracts.controller.js`, `CounterpartyDetail.controller.js`) has `.catch()` — `Home.controller.js` is the only exception
- The view/controller contract is misaligned: 6-tile view promise vs. 4-service implementation

## Proposed Solutions

### Option 1: Create PnlService + CashflowService + add .catch() (Recommended)

**Approach:**
1. Create `webapp/service/PnlService.js` following the pattern of `ContractsService.js`:
   ```js
   sap.ui.define([], function () {
     "use strict";
     return {
       getSummary: function () {
         return fetch("/api/pl/summary").then(function (r) { return r.json(); });
       }
     };
   });
   ```
2. Create `webapp/service/CashflowService.js` similarly, calling `/api/cashflow/summary`
3. Add both services to `Home.controller.js` imports and `_loadKpis`
4. Add `.catch()` to `_loadKpis` that calls `this.showError(this.getText("errLoadFailed"))`

**Pros:** Completes the feature as designed; consistent with all other controllers
**Cons:** Requires backend endpoints `/api/pl/summary` and `/api/cashflow/summary` to exist or be created
**Effort:** 2-3 hours (frontend) + backend work if endpoints don't exist
**Risk:** Medium — depends on backend APIs

---

### Option 2: Hide PnL and Cashflow tiles until backend is ready

**Approach:** Set `visible="{viewModel>/kpiPnlReady}"` on the PnL and Cashflow `GenericTile` elements, default to `false`. Add a TODO comment. Add `.catch()` immediately.

**Pros:** Stops showing broken "–" tiles; low risk; fix `.catch()` today
**Cons:** Doesn't resolve the underlying missing service problem; defers feature
**Effort:** 30 minutes
**Risk:** Very Low

---

### Option 3: Show a "Coming Soon" state on PnL/Cashflow tiles

**Approach:** Set `frameType="TwoByHalf"` and add a `GenericTile` `state="Disabled"` to indicate the feature is pending. Retains the visual but communicates intent.

**Pros:** Better UX than "–"; communicates roadmap intent
**Cons:** Still deferred; requires UX decision
**Effort:** 1 hour
**Risk:** Low

## Recommended Action

**Immediate:** Apply Option 2 to stop showing broken data (30 min). In parallel, implement Option 1 once the backend endpoints are confirmed to exist (check `backend/app/api/` for PnL and Cashflow routes).

## Technical Details

**Affected files:**
- `webapp/controller/Home.controller.js` — add imports, extend `loadParallel` call, add `.catch()`
- `webapp/service/PnlService.js` — create new file
- `webapp/service/CashflowService.js` — create new file
- `webapp/view/Home.view.xml` — optionally add `visible` binding if using Option 2/3

**Backend endpoints to verify/create:**
- `GET /api/pl/summary` — should return `{ total_pnl: number, currency: string }`
- `GET /api/cashflow/summary` — should return `{ net_30d: number, currency: string }`

**Related components:**
- `webapp/i18n/i18n.properties`: `homeKpiPnl`, `homeKpiPnlSub`, `homeKpiCashflow`, `homeKpiCashflowSub` (already present)

**Database changes:** No

## Acceptance Criteria

- [ ] Home dashboard shows no tiles permanently stuck at "–"
- [ ] `_loadKpis` has a `.catch()` handler that shows `errLoadFailed` message
- [ ] PnL tile shows a real value or a clear "unavailable" state (not "–")
- [ ] Cashflow tile shows a real value or a clear "unavailable" state
- [ ] Browser console shows no unhandled promise rejection from `_loadKpis`
- [ ] `PnlService.js` and `CashflowService.js` follow the existing service module pattern

## Work Log

### 2025-01-31 - Discovered in architecture review

**By:** Architecture-strategist agent + code reading

**Actions:**
- Confirmed `webapp/service/` has no PnlService or CashflowService
- Confirmed view declares 6 tiles, controller only populates 4
- Confirmed missing `.catch()` in `_loadKpis` (every other controller has one)
- Rated P1: 2 of 6 dashboard tiles are permanently broken, visible to all users on app startup
