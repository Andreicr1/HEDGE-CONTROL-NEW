---
title: "SAP UI5 Parallel TODO Resolution: P1/P2/P3 Bug Fixes in HEDGE-CONTROL-NEW"
date: "2026-03-10"
problem_type: "ui-bugs"
component: "frontend/webapp (SAP UI5), backend/app/api (FastAPI)"
symptoms:
  - "VizFrame charts silently misconfigured (uiConfig parsed as binding expression)"
  - "2 of 6 Home KPI tiles permanently showing dash (missing backend endpoints)"
  - "Memory leak multiplying API calls N× per navigation session"
  - "Session expiry shows frozen spinner instead of redirect"
  - "~4MB sap.viz library loaded on every page including non-chart pages"
  - "KPI refresh transfers ~7.5MB when only a count is needed"
  - "Race condition: rapid refresh overwrites fresh data with stale"
tags:
  - sapui5
  - fastapi
  - memory-leak
  - performance
  - security
  - binding
  - router
  - csrf
  - i18n
severity: "p1-p2-p3"
status: "resolved"
commit: "df74723"
branch: "feat/frontend-enterprise-ux-upgrade"
---

# SAP UI5 Batch Fixes: P1/P2/P3 — HEDGE-CONTROL-NEW

13 TODOs resolved across three priority tiers in one session using parallel subagents (Wave 1: 8 in parallel → Wave 2: 4 in parallel → Wave 3: 1 sequential).

## Solutions

### P1: VizFrame uiConfig Binding Fix

**Root cause:** In SAP UI5, any XML attribute value starting with `{` is parsed as a **data binding expression**. The existing `uiConfig="{applicationSet: 'fiori', scale: {theme: 'sap_horizon'}}"` was being treated as a model path, not an object literal — silently dropping chart configuration. Since `applicationSet: 'fiori'` is the sap_horizon default anyway, the entire attribute was unnecessary.

**Affected files:** `Cashflow.view.xml`, `Pnl.view.xml`, `Mtm.view.xml`

**Fix:** Remove `uiConfig` attribute from all VizFrame XML elements.

```xml
<!-- BEFORE (broken — UI5 parses as binding expression) -->
<viz:VizFrame id="cashflowChart" vizType="line" width="100%" height="300px"
  visible="{cf>/projectionLoaded}"
  uiConfig="{applicationSet: 'fiori', scale: {theme: 'sap_horizon'}}">

<!-- AFTER (correct — uiConfig omitted; sap_horizon defaults apply) -->
<viz:VizFrame id="cashflowChart" vizType="line" width="100%" height="300px"
  visible="{cf>/projectionLoaded}">
```

**Rule:** Never use `{...}` object literal syntax in XML attributes for complex UI5 properties. Use `setVizProperties()` / `setUiConfig()` programmatically in `onAfterRendering` if needed.

---

### P1: Home KPI Tiles Hidden Until Backend Ready

**Root cause:** Two KPI tiles (`kpiPnlValue`, `kpiCashflowValue`) were bound to model properties but no backend `/summary` endpoint existed to populate them. They showed "–" permanently with no indication they were broken.

**Fix:** Add `kpiPnlReady: false` / `kpiCashflowReady: false` to the view model, bind `visible` on each tile. The tiles are hidden until backend endpoints are ready.

```javascript
// Home.controller.js — onInit viewModel
this.initViewModel("home", {
  kpiPnlValue: "–",
  kpiPnlColor: "Neutral",
  kpiPnlReady: false,          // ← controls tile visibility
  kpiCashflowValue: "–",
  kpiCashflowReady: false,     // ← controls tile visibility
  // ...
});
```

```xml
<!-- Home.view.xml -->
<GenericTile id="kpiPnl" visible="{home>/kpiPnlReady}" ...>
<GenericTile id="kpiCashflow" visible="{home>/kpiCashflowReady}" ...>
```

**Rule:** Every view binding must have a corresponding backend endpoint. When a backend is not yet ready, use a `visible` binding bound to a `false` flag — not a placeholder "–" that looks like a real (but empty) value.

---

### P1: Router Listener Memory Leak

**Root cause:** All detail controllers (`CounterpartyDetail`, `OrderDetail`, `LinkageDetail`, `DealDetail`, `ExposureDetail`, `ContractDetail`, `RfqDetail`) attached route pattern-matched listeners in `onInit` via `attachPatternMatched(this._onRouteMatched, this)` but had empty `onExit: function () {}` stubs. Each navigation to a detail page registered a new listener. After N navigations, `_onRouteMatched` fired N times, multiplying API calls geometrically.

**Fix:** `onExit` must call `detachPatternMatched` with the exact same function reference and context:

```javascript
// CounterpartyDetail.controller.js
onInit: function () {
  this.getRouter().getRoute("counterpartyDetail")
    .attachPatternMatched(this._onRouteMatched, this);
},

onExit: function () {
  this.getRouter().getRoute("counterpartyDetail")
    .detachPatternMatched(this._onRouteMatched, this);  // ← same fn + context
},
```

**Special case — RfqDetail:** Attaches to two routes (`rfqDetail` + `rfqDocument`). Both must be detached, plus `_stopPolling()`:

```javascript
onExit: function () {
  this._stopPolling();
  this.getRouter().getRoute("rfqDetail").detachPatternMatched(this._onRouteMatched, this);
  this.getRouter().getRoute("rfqDocument").detachPatternMatched(this._onRouteMatched, this);
},
```

**Rule:** Every `attachPatternMatched` or `attachRouteMatched` in `onInit` must have a matching `detachPatternMatched` in `onExit`. Empty `onExit` stubs are a code smell — treat as incomplete.

---

### P1: loadParallel Error Handling + Security Logging

**Root cause:** `BaseController.loadParallel` used `Promise.all(fns.map(fn => fn().catch(() => null)))` — silencing every HTTP error. A 401 (session expired) showed a frozen loading spinner instead of redirecting to login.

**Fix:** Remove per-promise `.catch(() => null)`. Add a top-level `.catch` with status classification:

```javascript
// BaseController.js
loadParallel: function (aFnCalls) {
  return Promise.all(aFnCalls.map(function (fn) { return fn(); }))
    .catch(function (oErr) {
      var iStatus = oErr && oErr.status;
      if (iStatus === 401) {
        console.warn("[SECURITY] SESSION_EXPIRED", { url: oErr.url, ts: Date.now() });
        window.location.href = "/";
      } else if (iStatus === 403) {
        console.warn("[SECURITY] ACCESS_DENIED", { url: oErr.url, ts: Date.now() });
      } else if (iStatus === 429) {
        console.warn("[SECURITY] RATE_LIMITED", { url: oErr.url, ts: Date.now() });
      } else {
        console.error("[APP] LOAD_FAILURE", oErr);
      }
      return Promise.reject(oErr);  // re-throw so callers can handle too
    });
},
```

**Note:** The `apiClient.js` already checks `response.ok` and throws structured errors with `.status` and `.url`. No changes needed to service files.

**Rule:** Never use `.catch(() => null)` in a shared parallel-load utility. Errors must propagate so the UI can react (show error state, redirect, log).

---

### P2: Dead Fragment Cleanup + KpiCard Event Binding

**Root cause:** `EntityHeader.fragment.xml` was fully dead (no `loadFragment()` call in any controller). `KpiCard.fragment.xml` used `press="{press}"` — in SAP UI5, `press` is an **event**, not a property, so data binding with `{...}` syntax is invalid and would throw a runtime exception.

**Fix:**
- Delete `EntityHeader.fragment.xml` entirely
- Change `press="{press}"` → `press=".onKpiTilePress"` in KpiCard

```xml
<!-- BEFORE (runtime crash if ever loaded) -->
<GenericTile press="{press}" ...>

<!-- AFTER (static handler reference — valid UI5 syntax) -->
<GenericTile press=".onKpiTilePress" ...>
```

**Rule:** Events (`press`, `change`, `select`) cannot be data-bound. Only properties and aggregations support binding. Grep for `press="{` in XML files to catch this class of bug.

---

### P2: CounterpartyDetail Empty State Consistency

**Root cause:** All 9 list views used `<IllustratedMessage>` inside `<Table noData>` aggregation. `CounterpartyDetail.view.xml` used plain `noDataText="..."` attribute — visible inconsistency to users navigating between screens.

**Fix:**

```xml
<!-- BEFORE -->
<Table items="{cptyDet>/contracts}" noDataText="{i18n>noContractsForCounterparty}">

<!-- AFTER -->
<Table items="{cptyDet>/contracts}">
  <noData>
    <IllustratedMessage
      illustrationType="sapIllus-EmptyList"
      title="{i18n>noContractsForCounterparty}"
      description="{i18n>emptyStateDescription}" />
  </noData>
```

**Note:** The view's default namespace is `xmlns="sap.m"`, so no prefix needed for `IllustratedMessage`. The description key is `emptyStateDescription` (not `noDataDescription`).

---

### P2: sap.viz Lazy Loading

**Root cause:** `sap.viz` (~3.8MB) was listed in `manifest.json` global libs, loading on every page — including Contracts, Orders, Counterparties which have no charts.

**Fix:** One-line manifest change:

```json
// manifest.json — before
"sap.viz": {}

// manifest.json — after
"sap.viz": { "lazy": true }
```

**Impact:** ~800ms faster TTI on non-chart pages. Library loads on demand when `Home.view.xml` (or any analytics view) is first parsed.

**Rule:** Any UI5 library > 500KB should have `"lazy": true` unless used on the app's landing page. Audit `manifest.json` in architecture reviews.

---

### P2: KPI Count Endpoints (7.5MB → ~120 bytes per refresh)

**Root cause:** `_loadKpis` called `ordersService.list()`, `contractsService.list()`, `rfqService.list()` but only used `.length`. At 5,000 records × ~500 bytes = 7.5MB transferred just for three counts.

**Backend — add `/count` endpoints to each router:**

```python
# backend/app/api/routes/orders.py
@router.get("/count")
def get_orders_count(
    _: None = Depends(require_any_role("trader", "risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> dict:
    count = session.query(Order).filter(Order.deleted_at.is_(None)).count()
    return {"count": count}
```

Pattern applied to `/orders/count`, `/contracts/hedge/count`, `/rfqs/count`.

**Frontend — add `getCount()` to each service:**

```javascript
// ordersService.js (+ contractsService.js + rfqService.js)
getCount: function () {
  return apiClient.getJson("/orders/count");
}
```

**Home controller — call `getCount()` instead of `list()`:**

```javascript
this.loadParallel([
  function () { return exposuresService.getNet(); },
  function () { return ordersService.getCount(); },    // ← was .list()
  function () { return contractsService.getCount(); }, // ← was .list()
  function () { return rfqService.getCount(); }        // ← was .list()
]).then(function (aResults) {
  oModel.setProperty("/kpiOrdersCount",
    typeof (aResults[1] && aResults[1].count) === "number" ? String(aResults[1].count) : "–");
  // ...
```

**Rule:** If only `.length` is needed, never call a list endpoint. Add a dedicated count endpoint. `SELECT COUNT(*)` is O(1) on indexed columns vs. O(n) full scan + serialization.

---

### P2: KPI Refresh Concurrency Guard

**Root cause:** Rapid Refresh button clicks launched multiple concurrent `Promise.all` chains, all writing to the same model properties. Last response to arrive (not necessarily the most recent) overwrote fresher data.

**Fix:** In-flight boolean flag — simplest and safest pattern:

```javascript
// Home.controller.js
_bLoadingKpis: false,

_loadKpis: function () {
  if (this._bLoadingKpis) { return; }   // ← gate: drop concurrent calls
  this._bLoadingKpis = true;

  this.loadParallel([...])
    .then(function (aResults) { /* ... */ }.bind(this))
    .catch(function () { /* ... */ }.bind(this))
    .finally(function () {
      this._bLoadingKpis = false;        // ← always reset, even on error
    }.bind(this));
},
```

**Why `.finally()` is critical:** If only `.then()` resets the flag, any error leaves `_bLoadingKpis = true` permanently, locking the refresh forever.

**Rule:** Any user-triggered function that fires async network requests must guard against concurrent execution with an in-flight flag. Use `.finally()` to release the guard.

---

### P2: CSRF Audit (JWT Bearer = No Risk)

**Findings:** Backend uses JWT bearer token authentication exclusively:
- `auth.py` extracts token from `Authorization: Bearer <token>` header
- No `SessionMiddleware`, no cookie-based auth
- CORS configured with `allow_credentials=False`

**Conclusion:** CSRF is mitigated by design. Bearer tokens in the `Authorization` header are not automatically sent cross-origin by browsers. No CSRF middleware or `X-CSRF-Token` headers needed.

**Security logging added to `loadParallel`** (see P1 fix above) covers all auth-related frontend events.

---

### P3: Dead CSS Removal

**Root cause:** Three CSS classes (`.hcKpiPositive`, `.hcKpiNegative`, `.hcKpiCritical`) were defined in `style.css` but never applied in any view — the codebase uses `valueColor` binding on `NumericContent` instead. Additionally, `.hcKpiCritical` mapped to `var(--sapNegativeColor)` (red) instead of `var(--sapCriticalColor)` (amber) — wrong token.

**Fix:** Delete all three rules. No view references them.

```css
/* DELETED — dead code, wrong token on hcKpiCritical */
.hcKpiPositive .sapMNCSValue { color: var(--sapPositiveColor); }
.hcKpiNegative .sapMNCSValue { color: var(--sapNegativeColor); }
.hcKpiCritical .sapMNCSValue { color: var(--sapNegativeColor); } /* ← was wrong */
```

**SAP token reference:**
- `--sapPositiveColor` → green (Good)
- `--sapNegativeColor` → red (Error)
- `--sapCriticalColor` → amber/orange (Critical — e.g. warning threshold)

---

### P3: i18n Cleanup + MONTHS Array Hoisting

**Root cause:**
1. Two orphan keys (`homeKpiMtTotal`, `homeKpiMtTotalSub`) referenced a removed KPI tile
2. MONTHS array declared **inside** the `.map()` callback — re-allocated on every iteration

**Fix A — Delete orphan keys from `i18n.properties`:**
```properties
# DELETED (no view references these):
homeKpiMtTotal=Mark-to-Market Total
homeKpiMtTotalSub=Total MtM across all instruments
```

**Fix B — Hoist MONTHS to module scope:**
```javascript
// Cashflow.controller.js — BEFORE (re-created on every .map() call)
_buildChartData: function (aData) {
  return aData.map(function (oItem) {
    var MONTHS = ["Jan","Fev","Mar",...];  // ← inside .map()!
    return { label: MONTHS[oItem.month - 1], ... };
  });
}

// AFTER — allocated once at module load
var MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];

// ...in controller:
_buildChartData: function (aData) {
  return aData.map(function (oItem) {
    return { label: MONTHS[oItem.month - 1], ... };
  });
}
```

---

### P3: UUID Route Validation Guard

**Root cause:** Route parameters (e.g., `counterpartyId`, `orderId`) were passed directly to service calls without format validation. Garbage values like `"undefined"`, `":id"`, or empty strings could reach the backend.

**Fix — `_isValidId` helper in `BaseController`:**

```javascript
// BaseController.js
_isValidId: function (sId) {
  if (!sId || typeof sId !== "string") { return false; }
  var rUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  var rNumeric = /^\d+$/;
  return rUuid.test(sId) || rNumeric.test(sId);
},
```

**Usage in every detail controller:**

```javascript
_onRouteMatched: function (oEvent) {
  this._sId = oEvent.getParameter("arguments").counterpartyId;
  if (!this._isValidId(this._sId)) {
    this.getRouter().navTo("notFound");
    return;
  }
  this._loadData();
},
```

Applied to: `CounterpartyDetail`, `OrderDetail`, `LinkageDetail`, `DealDetail`, `ExposureDetail`, `ContractDetail`.

---

## Related Documentation

- **[Heal frontend-design skill for SAP UI5](../../skill-maintenance/heal-frontend-design-skill-for-sap-ui5.md)** — SAP UI5 XML view skeletons, controller patterns, model/binding conventions, CSS using SAP design tokens, i18n requirements, error handling patterns, and screen-type guides (List, Detail, Create/Edit).

- **[Frontend Enterprise UX Upgrade Plan](../../../plans/2026-03-09-feat-frontend-enterprise-ux-upgrade-plan.md)** — 5-phase plan covering Design System Foundation, Home Dashboard KPIs, List Views migration, Detail Views (ObjectPageLayout), Analytics (VizFrame), and UX Polish. Includes architecture decisions, error propagation patterns, and state lifecycle risks.

- **[FastAPI RBAC Gap: `get_current_user` vs `require_any_role`](../../security-issues/fastapi-missing-rbac-require-any-role.md)** — Critical security fix for RBAC enforcement gaps on mutating endpoints; prevention strategies and Semgrep-based CI enforcement.

---

## Prevention Strategies

### Code Review Checklist

**SAP UI5 Patterns:**
- [ ] VizFrame and complex UI5 configs use programmatic setters, not XML `{...}` attribute syntax
- [ ] All Fragment event bindings reference actual controller methods (no `press="{press}"`)
- [ ] Empty-state handling uses consistent pattern across all views (IllustratedMessage everywhere)
- [ ] `onInit` route listeners have matching `onExit` detach — empty `onExit` stubs are flagged
- [ ] Every `attachPatternMatched` has a corresponding `detachPatternMatched` in `onExit`
- [ ] Data binding contracts match backend response shape (KPI tiles, counts, nested objects)
- [ ] Heavy libraries (sap.viz, sap.ui.table) use `"lazy": true` in manifest

**API Design:**
- [ ] Count-only use cases use dedicated `/count` endpoints — never full list + `.length`
- [ ] Route parameters validated (type, format) before passing to service layer
- [ ] No `.catch(() => null)` silencing HTTP errors; errors propagate and are classified
- [ ] In-flight flag prevents duplicate concurrent requests on user-triggered data loads
- [ ] Backend endpoint contract documented (field names, types, optional fields)

**Security & Auth:**
- [ ] Authentication mechanism explicitly documented (JWT/CSRF/session) in architecture review
- [ ] 401 session expiry redirects to login — not silent frozen spinner
- [ ] 403 access denial logged with structured format

**Performance:**
- [ ] No full-list fetches for count-only use cases
- [ ] Heavy UI5 libraries lazy-loaded
- [ ] Locale strings externalized in i18n bundles — never hardcoded in loops or callbacks

### Architectural Rules

1. **Component Config Rule:** UI5 component properties accepting objects must be set programmatically — never as XML string attributes with `{...}` syntax.
2. **Data Contract Rule:** Every view binding to a backend field must have a verified backend response shape. Broken tiles that show "–" are worse than hidden tiles.
3. **Lifecycle Cleanup Rule:** Every router listener/timer attached in `onInit` must have a matching detach in `onExit`. Empty `onExit` stubs = incomplete implementation.
4. **Error Handling Rule:** HTTP promise chains classify errors per status code. Never use blanket `.catch(() => null)`.
5. **Event Binding Rule:** Fragment event attributes reference only methods that exist in the parent controller. Validate at code review — not at runtime.
6. **Consistency Rule:** Single empty-state pattern across all views (IllustratedMessage preferred for Fiori compliance).
7. **Library Loading Rule:** Identify heavy UI5 libraries upfront; document lazy-loading strategy.
8. **Concurrency Rule:** User-triggered data loads use in-flight flags; `.finally()` releases the flag even on error.
9. **Route Validation Rule:** Route parameters validated (UUID or numeric) before any service call.
10. **Locale Rule:** All user-facing strings in loops/callbacks come from resource bundles — no hardcoded locale-specific text.

### Detection

**Pre-Commit / Linting:**
- Grep pattern: `press="{"` in XML files → invalid event binding
- Grep pattern: `\.catch\(\s*function\s*\(\s*\)\s*\{\s*return null` → error silencing
- Grep pattern: `onExit: function \(\) \{\}` → empty lifecycle hook
- Grep pattern: `attachPatternMatched` without corresponding `detachPatternMatched`

**Architecture Review (Per Sprint):**
- Audit `manifest.json` for heavy libs without `"lazy": true`
- Audit service layer for in-flight flags on user-triggerable loads
- Check all views for consistent empty-state pattern
- Verify auth mechanism documented and 401 handling tested

**Static Analysis:**
- Orphaned CSS classes: grep class names from `.css` against all `.xml`/`.js` files
- Hardcoded locale strings: non-ASCII text in controller source outside i18n model
- Full-list count pattern: `.list()` call result immediately used only as `.length`
