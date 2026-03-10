---
status: done
priority: p2
issue_id: "009"
tags: [ui5, concurrency, refresh-guard, home-controller]
dependencies: ["008"]
---

# Add Refresh Debounce Guard to _loadKpis

## Problem Statement

`Home.controller.js._loadKpis` has no guard against concurrent executions. If a user clicks the Refresh button rapidly, each click launches a new set of 4 (or 6, after todo 002) API calls. All outstanding calls run in parallel, and the **last response to arrive — not necessarily the last to be sent — wins**. This creates a race condition where stale data can overwrite fresher data in the view model. The loading spinner does not prevent this.

## Findings

- `webapp/controller/Home.controller.js` refresh handler (inferred): calls `this._loadKpis()` without checking if a load is already in progress
- `_loadKpis` does not set, check, or clear any `_bRefreshing` flag
- `loadParallel` returns a `Promise.all` that resolves when all 4 calls complete; if a second `_loadKpis()` is triggered mid-flight, there are now 2 in-flight `Promise.all` chains, each writing to the same view model properties
- Real-world trigger: users on slow connections who click Refresh 2-3 times impatiently

**Example race condition:**
1. t=0: Click 1 fires calls A1, A2, A3, A4
2. t=100ms: Click 2 fires calls B1, B2, B3, B4
3. t=320ms: B1-B4 complete first (faster response) → model updated
4. t=450ms: A1-A4 complete → model overwritten with **older** data

## Proposed Solutions

### Option 1: In-flight flag guard (Recommended — Minimal Change)

**Approach:**
```js
_bLoadingKpis: false,

_loadKpis: function () {
  if (this._bLoadingKpis) { return; }
  this._bLoadingKpis = true;
  var oVM = this.getModel("viewModel");
  oVM.setProperty("/loading", true);

  this.loadParallel([/* ... */])
    .then(function (aResults) {
      // ... set properties ...
    })
    .catch(function (oErr) {
      this.showError(this.getText("errLoadFailed"));
    }.bind(this))
    .finally(function () {
      this._bLoadingKpis = false;
      oVM.setProperty("/loading", false);
    }.bind(this));
},
```

**Why `.finally()` is critical:** The guard must be released even if the promise rejects. Using only `.then()` would create a permanent lock after any error.

**Pros:** 5-line change; prevents race; doesn't add dependencies
**Cons:** Silently drops rapid clicks (not debounce — it's a gate). First click always wins; subsequent clicks while loading are no-ops.
**Effort:** 15 minutes
**Risk:** Very Low

---

### Option 2: Abort previous request and start fresh (debounce-cancel)

**Approach:** Use `AbortController` to cancel the previous in-flight requests when a new Refresh is initiated.

```js
_oAbortController: null,

_loadKpis: function () {
  if (this._oAbortController) { this._oAbortController.abort(); }
  this._oAbortController = new AbortController();
  var oSignal = this._oAbortController.signal;
  // pass signal to each fetch call
  fetch("/api/orders/", { signal: oSignal })...
},
```

**Pros:** Most correct semantically — always shows the most recently requested data
**Cons:** Requires passing `AbortSignal` through service layer; more invasive change; services must handle `AbortError`
**Effort:** 2-3 hours
**Risk:** Low-medium

---

### Option 3: Disable Refresh button while loading

**Approach:** Add `enabled="{viewModel>/loadingComplete}"` to the Refresh button. User can't click it while loading.

**Pros:** User-visible feedback; simple
**Cons:** Doesn't prevent programmatic re-trigger; poor UX on slow connections (button unusable for seconds)
**Effort:** 15 minutes
**Risk:** Very Low

## Recommended Action

Apply **Option 1** immediately — it's the simplest, safest, and most idiomatic. Add the `_bLoadingKpis` flag and `.finally()` in a 15-minute change. Combine with Option 3 (disable button) for better UX, which takes another 5 minutes.

## Technical Details

**Affected files:**
- `webapp/controller/Home.controller.js` — add `_bLoadingKpis` property and modify `_loadKpis`

**Note on `.finally()`:** SAP UI5 targets ES6+; `Promise.prototype.finally` is available in UI5 1.52+ (polyfilled). This app targets UI5 1.136 — safe to use.

**Note on dependency:** Todo 008 (count endpoints) and this todo are independent. The guard applies whether using full `.list()` or lightweight `.getCount()`. However, fixing the overfetch (todo 008) reduces the window in which the race can occur.

**Database changes:** No

## Acceptance Criteria

- [ ] Rapid clicking of Refresh (5× in 500ms) results in exactly one set of API calls completing and updating the model
- [ ] The loading spinner correctly appears and disappears for the single execution
- [ ] If `_loadKpis` throws (network error), `_bLoadingKpis` is reset to `false` (verified via `.finally()`)
- [ ] KPI values are correct — no stale data overwrites fresh data
- [ ] No regression in normal single-click behavior

## Work Log

### 2025-01-31 - Discovered in performance review

**By:** performance-oracle agent

**Actions:**
- Identified absence of concurrency guard on `_loadKpis`
- Modeled race condition scenario with request timing
- Rated P2: Race condition can display stale data; simple fix available
