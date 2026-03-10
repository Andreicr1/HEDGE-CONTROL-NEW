---
status: done
priority: p3
issue_id: "012"
tags: [ui5, i18n, localization, cashflow, debt]
dependencies: ["005"]
---

# Clean Up Orphan i18n Keys and Hardcoded Portuguese Month Names

## Problem Statement

Two related but separable localization debt items:

1. **6 orphan i18n keys**: Defined in `webapp/i18n/i18n.properties` but referenced by no view, controller, or active fragment. These keys were added for feature code (ConfirmDialog) that was never activated or was removed, or for KPI tiles that no longer exist in the current form.

2. **Hardcoded Portuguese month abbreviations**: `Cashflow.controller.js` (or `Home.controller.js`) declares `["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]` as a literal array inside a `.map()` callback. This is not localized, not translatable, and is re-allocated on every chart data rebuild call.

## Findings

### Orphan i18n Keys

The following keys exist in `webapp/i18n/i18n.properties` but are unreferenced in any live code:

| Key | Origin | Status |
|-----|--------|--------|
| `homeKpiMtTotal` | Possibly removed KPI tile | Delete — no corresponding view binding |
| `homeKpiMtTotalSub` | Possibly removed KPI tile subtitle | Delete |
| `confirmDelete` | `ConfirmDialog.fragment.xml` (dead fragment) | Keep until todo 005 resolves fragment fate |
| `btnConfirm` | `ConfirmDialog.fragment.xml` (dead fragment) | Keep until todo 005 resolves fragment fate |
| `btnCancel` | `ConfirmDialog.fragment.xml` (dead fragment) | Keep until todo 005 resolves fragment fate |
| `confirmTitle` | `ConfirmDialog.fragment.xml` (dead fragment) | Keep until todo 005 resolves fragment fate |

**Immediate safe deletions:** `homeKpiMtTotal` and `homeKpiMtTotalSub` — these reference a KPI tile that doesn't exist in the current Home view.

**Deferred deletions (after todo 005):** If `ConfirmDialog.fragment.xml` is deleted, also delete `confirmDelete`, `btnConfirm`, `btnCancel`, `confirmTitle`.

### Hardcoded MONTHS Array

In `Cashflow.controller.js` or `Home.controller.js`, the chart data build method:
```js
_buildChartData: function (aData) {
  return aData.map(function (oItem) {
    var aMonths = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
    //             ^ declared inside .map() — re-created on every iteration
    return { month: aMonths[oItem.month - 1], value: oItem.net_cashflow };
  });
},
```

**Issues:**
1. Portuguese-only: Not translatable without code changes; breaks UI for non-Portuguese locales
2. Re-allocated on every `.map()` iteration: garbage collector pressure (minor but unnecessary)
3. Not using `Date.toLocaleDateString` or the i18n model

## Proposed Solutions

### Part A: Orphan i18n Key Cleanup

**Immediate action — delete the confirmed-safe keys:**
```properties
# DELETE:
homeKpiMtTotal=Mark-to-Market Total
homeKpiMtTotalSub=Total MtM across all instruments
```

**Deferred — add TODO comments next to ConfirmDialog keys:**
```properties
# TODO: delete if ConfirmDialog.fragment.xml is removed (see todos/005)
confirmDelete=Delete this record?
btnConfirm=Confirm
btnCancel=Cancel
confirmTitle=Confirm Action
```

### Part B: Fix Hardcoded MONTHS Array

**Option 1: Move to module scope (quick fix, still not i18n):**
```js
// At module level, after sap.ui.define header:
var MONTHS = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];

// In _buildChartData:
_buildChartData: function (aData) {
  return aData.map(function (oItem) {
    return { month: MONTHS[oItem.month - 1], value: oItem.net_cashflow };
  });
},
```

**Option 2: Use JavaScript Date API for proper i18n (Recommended):**
```js
_buildChartData: function (aData) {
  return aData.map(function (oItem) {
    var oDate = new Date(2000, oItem.month - 1, 1); // Year doesn't matter for month name
    var sMonth = oDate.toLocaleDateString(sap.ui.getCore().getConfiguration().getLanguage(), {
      month: "short"
    });
    return { month: sMonth, value: oItem.net_cashflow };
  });
},
```

**Option 3: Add month abbreviations to i18n.properties:**
```properties
month.jan=Jan
month.feb=Fev
# ... etc.
```
Then use `this.getText("month." + oItem.month)`. This is the most UI5-canonical approach but adds 12 keys.

## Recommended Action

1. **Immediately (5 min):** Delete `homeKpiMtTotal` and `homeKpiMtTotalSub` from `i18n.properties`
2. **Immediately (10 min):** Apply Part B Option 1 — move `MONTHS` to module scope (eliminates re-allocation, easy first step)
3. **Before localization:** Apply Part B Option 2 — use Date API for proper i18n if the app will be used in non-Portuguese locales

## Technical Details

**Affected files:**
- `webapp/i18n/i18n.properties` — delete 2-6 orphan keys
- `webapp/controller/Home.controller.js` or `webapp/controller/Cashflow.controller.js` — move MONTHS constant to module scope

**i18n.properties verification:**
Before deleting any key, run a global `grep -r "homeKpiMtTotal" webapp/` to confirm no view, fragment, or controller references it.

**Database changes:** No

## Acceptance Criteria

- [ ] `homeKpiMtTotal` and `homeKpiMtTotalSub` are removed from `i18n.properties`
- [ ] Grep confirms no view or controller references the deleted keys
- [ ] `MONTHS` array is declared outside of the `.map()` callback (at minimum, module-scope constant)
- [ ] Chart still renders correct month abbreviations after the refactor
- [ ] TODO comments added to ConfirmDialog-related i18n keys (or they are deleted if todo 005 removes the fragment)
- [ ] No regression in cashflow/chart data building

## Work Log

### 2025-01-31 - Discovered in architecture and code-simplicity review

**By:** architecture-strategist agent + code-simplicity-reviewer agent

**Actions:**
- Identified 6 orphan i18n keys via cross-reference of i18n.properties against all view/controller files
- Confirmed MONTHS array is declared inside .map() callback (per code-simplicity-reviewer)
- Confirmed MONTHS is hardcoded Portuguese (not using i18n model)
- Rated P3: Technical debt; low impact but easy to fix; localization gap if app goes multi-locale
