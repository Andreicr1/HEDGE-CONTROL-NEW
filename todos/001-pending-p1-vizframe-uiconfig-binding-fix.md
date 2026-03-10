---
status: done
priority: p1
issue_id: "001"
tags: [ui5, charts, vizframe, binding]
dependencies: []
---

# Fix VizFrame `uiConfig` Broken Binding Expression

## Problem Statement

The `VizFrame` controls in `Home.view.xml` (and analytics views) set `uiConfig` as an XML attribute using `{...}` syntax. In SAP UI5, any attribute value starting with `{` is parsed as a **data binding expression** — not a JavaScript object literal. The chart renders without Fiori application set and without horizon theme scaling. The failure is silent (a framework warning, not a thrown error), so it passes casual QA while producing a broken chart configuration.

## Findings

- `webapp/view/Home.view.xml:68`: `uiConfig="{applicationSet: 'fiori', scale: {theme: 'sap_horizon'}}"` — UI5 binding parser sees `applicationSet` as a model path and silently drops the attribute
- The nested `{theme: 'sap_horizon'}` inside `scale` further confuses the binding parser (nested braces)
- VizFrame `setUiConfig()` must be called **before** data is bound to take effect; `onAfterRendering` may be too late
- All three analytics controllers (`Cashflow`, `Pnl`, `Mtm`) share this pattern
- Confirmed: only `Home.view.xml` contains a VizFrame in this codebase revision (the cashflow chart)

## Proposed Solutions

### Option 1: Set `uiConfig` programmatically in `onInit` before data bind (Recommended)

**Approach:** Remove the `uiConfig` attribute from XML entirely. In each analytics controller's `onInit`, after `this.byId("cashflowChart")` is available (which requires the view to be rendered), use `setVizProperties` for theme-level properties and rely on the framework default for `applicationSet`.

```js
// Home.controller.js — onAfterRendering or after fragment is loaded
onAfterRendering: function () {
    var oChart = this.byId("cashflowChart");
    if (oChart) {
        oChart.setVizProperties({
            general: { background: { visible: false } }
        });
        // applicationSet 'fiori' is the default in sap_horizon — can be omitted
    }
},
```

**Pros:** Correct UI5 pattern; no binding confusion; controller owns chart config
**Cons:** Requires `onAfterRendering` lifecycle hook to be added
**Effort:** 1 hour
**Risk:** Low

---

### Option 2: Use a named model property to pass the config object

**Approach:** Store the config object in the `viewModel` JSONModel and bind it via a path:

```js
// In onInit
oVM.setProperty("/chartUiConfig", { applicationSet: "fiori", scale: { theme: "sap_horizon" } });
```

```xml
<!-- In view -->
<viz:VizFrame uiConfig="{viewModel>/chartUiConfig}" />
```

**Pros:** Keeps config in the view declaratively; supports runtime config changes
**Cons:** Binding to a complex object via JSONModel works but is indirect; requires verifying VizFrame accepts an object binding
**Effort:** 1-2 hours
**Risk:** Medium (VizFrame binding behavior with object properties requires testing)

## Recommended Action

Apply **Option 1** across all views with VizFrame controls. Remove the `uiConfig` attribute from XML. For the Fiori application set specifically, verify whether the default in UI5 1.136+ with sap_horizon is already `'fiori'` (it is) — meaning the attribute may be entirely unnecessary once the binding error is removed.

## Technical Details

**Affected files:**
- `webapp/view/Home.view.xml:68` — `uiConfig` attribute on `viz:VizFrame#cashflowChart`

**Related components:**
- `webapp/controller/Home.controller.js` — needs `onAfterRendering` or chart init method
- sap.viz library (ensure it is loaded lazily per todo-008)

**Database changes:** No

## Acceptance Criteria

- [ ] No UI5 binding parse warning for `uiConfig` in browser console
- [ ] VizFrame renders with correct Fiori visual style (grouped bar chart uses sap_horizon token colors)
- [ ] `uiConfig` is not set via XML attribute `{...}` syntax in any view
- [ ] Chart data still loads and renders correctly after the fix

## Work Log

### 2025-01-31 - Discovered in architecture review

**By:** Architecture-strategist agent + code reading

**Actions:**
- Identified that `{applicationSet: 'fiori', scale: {theme: 'sap_horizon'}}` is parsed as a binding expression by UI5 XML parser
- Confirmed this is a P1 because chart configuration is silently broken in production
- Identified fix: remove from XML, apply programmatically in controller
