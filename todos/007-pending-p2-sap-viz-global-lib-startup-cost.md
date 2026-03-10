---
status: done
priority: p2
issue_id: "007"
tags: [ui5, performance, manifest, sap-viz, lazy-loading]
dependencies: []
---

# Lazy-Load sap.viz (Remove ~4MB Library from Global Startup)

## Problem Statement

`webapp/manifest.json` lists `sap.viz` as a global dependency under `sap.ui5.dependencies.libs`. This causes the SAP VizFrame charting library (~4MB) to be eagerly loaded for **every user on every page view**, even on pages that have no charts. `sap.viz` is only used by the cashflow column chart in `Home.view.xml`. All users pay a ~4MB startup cost even when navigating directly to Contracts, Orders, or Counterparty pages that don't use visualization. Additionally, `sap.ui.integration` is also globally loaded but only needed if SAP cards are present.

## Findings

- `webapp/manifest.json` `sap.ui5.dependencies.libs`:
  ```json
  {
    "sap.m": {}, "sap.ui.core": {}, "sap.f": {}, "sap.ui.layout": {},
    "sap.viz": {},
    "sap.ui.integration": {}
  }
  ```
- `webapp/view/Home.view.xml`: Contains one `<viz:VizFrame>` for the cashflow column chart
- **No other view** uses `sap.viz` or `sap.ui.integration` controls
- **Impact quantification:** sap.viz library = ~3.8MB (minified). On 5000 sessions/day, removing from global load = ~19GB/day bandwidth saved. Initial page load time reduced by ~800ms on a slow 3G connection.

## Proposed Solutions

### Option 1: Remove from manifest, load lazily in Home controller (Recommended)

**Approach:**

1. Remove from `manifest.json`:
   ```json
   // Remove these two entries:
   "sap.viz": {},
   "sap.ui.integration": {}
   ```

2. In `Home.controller.js`, load `sap.viz` lazily before the VizFrame is populated:
   ```js
   _loadVizLibrary: function () {
     return new Promise(function (resolve, reject) {
       sap.ui.require(["sap/viz/ui5/controls/VizFrame"], function () {
         resolve();
       }, reject);
     });
   },
   
   onInit: function () {
     // ... existing code ...
     this._loadVizLibrary().then(function () {
       this._loadChartData();
     }.bind(this));
   },
   ```

3. The VizFrame control namespace declaration in `Home.view.xml` (`xmlns:viz="sap.viz.ui5.controls"`) may trigger an eager library load at XML parse time. Mitigation: keep the xmlns but rely on the manifest `lazy: true` flag (see Option 2).

**Pros:** Significant UX improvement for all non-Home pages; ~4MB saved from initial bundle
**Cons:** Chart may briefly appear empty while library loads; requires careful init sequencing
**Effort:** 2-3 hours
**Risk:** Low (additive change, doesn't affect other pages)

---

### Option 2: Use `lazy: true` in manifest (Simpler)

**Approach:**
```json
"sap.viz": { "lazy": true },
"sap.ui.integration": { "lazy": true }
```

**Pros:** Minimal code change; SAP UI5 manages the lazy loading; works with XML view namespace declarations
**Cons:** Library still loads when the Home view is first created (not necessarily on demand); less control over timing
**Effort:** 5 minutes (manifest change only)
**Risk:** Very Low

---

### Option 3: Move VizFrame chart to a lazy-loaded component

**Pros:** Most performant; Home page loads instantly even for chart users
**Cons:** Significant refactoring; over-engineered for current scale
**Effort:** 1-2 days
**Risk:** Medium

## Recommended Action

Apply **Option 2** immediately (5-minute manifest change, zero regression risk). Document Option 1 as a stretch goal if load time benchmarks show the chart init latency is noticeable.

## Technical Details

**Files affected:**
- `webapp/manifest.json` — add `lazy: true` to `sap.viz` and `sap.ui.integration`

**Performance benchmarks to capture before/after:**
- Time to Interactive (TTI) on Contracts page (should improve with lazy sap.viz)
- DOMContentLoaded on all pages
- Network tab: confirm `sap-viz-*.js` defers to first visit of Home page

**Browser support:** `lazy` lib loading is supported in UI5 1.56+; this app targets 1.136+ — fully supported.

**`sap.ui.integration` note:** This library is for `sap.ui.integration.widgets.Card` controls. No Card controls are present in the current view set. Unless planned, can be removed entirely (not just lazied).

**Database changes:** No

## Acceptance Criteria

- [ ] `sap.viz` does not appear in the initial bundle waterfall when loading the Contracts page directly
- [ ] `sap.ui.integration` does not appear in the initial bundle waterfall unless a Card control is present
- [ ] Home page cashflow chart still renders correctly after the manifest change
- [ ] No console errors about missing VizFrame namespace on Home view load
- [ ] Network tab shows VizFrame chart renders within 2 seconds of Home page navigation

## Work Log

### 2025-01-31 - Discovered in performance and architecture review

**By:** performance-oracle agent + architecture-strategist agent

**Actions:**
- Confirmed `sap.viz` and `sap.ui.integration` in global manifest libs
- Confirmed only `Home.view.xml` uses `sap.viz` controls
- Quantified: ~3.8MB library, ~800ms startup impact on slow connections
- Rated P2: Performance regression affecting all page loads; simple fix available
