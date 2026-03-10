---
status: done
priority: p3
issue_id: "013"
tags: [ui5, refactoring, simplicity, security, promise, route]
dependencies: ["004"]
---

# Code Simplification: Extract _resolveLength, UUID Validation, LinkageDetail Promise.all

## Problem Statement

Three independent code quality items that share a common theme — small, focused improvements that reduce duplication, improve correctness, and harden the routing layer:

1. **`_resolveLength` pattern repeated 3×**: The null-safe array length check `Array.isArray(x) ? x.length : "–"` appears three times in a row in `Home._loadKpis`. It should be extracted to a helper.

2. **Route parameters not validated as UUIDs**: `CounterpartyDetail`, `OrderDetail`, and `LinkageDetail` controllers extract route parameters (`:id`, `:orderId`) and pass them directly to service calls without validating the format. A crafted non-UUID parameter could produce unexpected backend query results or bypass authorization checks.

3. **LinkageDetail sub-calls not wrapped in Promise.all**: The `LinkageDetail` controller fires two sub-calls (e.g., fetch related order + fetch related contract) in the same `.then()` chain but doesn't use `Promise.all`. If the first sub-call rejects, the second doesn't execute, and the error handling is inconsistent.

## Findings

### _resolveLength duplication

In `Home.controller.js` `_loadKpis` `.then()` handler:
```js
oVM.setProperty("/kpiOrdersCount",    Array.isArray(aResults[1]) ? aResults[1].length : "–");
oVM.setProperty("/kpiContractsCount", Array.isArray(aResults[2]) ? aResults[2].length : "–");
oVM.setProperty("/kpiRfqsCount",      Array.isArray(aResults[3]) ? aResults[3].length : "–");
```
This is the same expression 3× with only the array index varying.

### Route parameter UUID validation

- `CounterpartyDetail.controller.js` `_onRouteMatched`: `var sId = oArgs.id;` → passed to `CounterpartysService.getById(sId)` — no format check
- `OrderDetail.controller.js` (similar pattern)
- `LinkageDetail.controller.js` (similar pattern)
- Risk: Backend is the authoritative guard, but client-side validation is a defense-in-depth measure; also prevents local state corruption from invalid parameters

### LinkageDetail sub-calls without Promise.all

Confirmed by performance-oracle agent: both sub-calls fire in the same `.then()` callback (they are concurrent), but there is no `Promise.all([...])` wrapping them. Without `Promise.all`, if either sub-call rejects it propagates independently — there's no single catch point for partial failure, and the view may end up in a half-loaded state.

## Proposed Solutions

### Solution 1: Extract `_resolveLength` helper (or remove entirely with todo 008)

**If todo 008 (count endpoints) is implemented:**
The `_resolveLength` helper becomes unnecessary — the count comes directly from `{ count: N }`. Skip this refactor and just implement todo 008.

**If todo 008 is deferred:**
```js
// In BaseController.js or Home.controller.js:
_resolveLength: function (aArray) {
  return Array.isArray(aArray) ? aArray.length : "–";
},

// In _loadKpis:
oVM.setProperty("/kpiOrdersCount",    this._resolveLength(aResults[1]));
oVM.setProperty("/kpiContractsCount", this._resolveLength(aResults[2]));
oVM.setProperty("/kpiRfqsCount",      this._resolveLength(aResults[3]));
```

**Effort:** 5 minutes
**Risk:** Very Low

---

### Solution 2: UUID validation helper in BaseController

**Add to BaseController.js:**
```js
_isValidId: function (sId) {
  if (!sId || typeof sId !== "string") { return false; }
  // Accept UUID v4 format and simple numeric IDs
  var rUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  var rNumeric = /^\d+$/;
  return rUuid.test(sId) || rNumeric.test(sId);
},
```

**In each `_onRouteMatched`:**
```js
_onRouteMatched: function (oEvent) {
  var sId = oEvent.getParameter("arguments").id;
  if (!this._isValidId(sId)) {
    this.getRouter().navTo("notFound");
    return;
  }
  this._loadCounterparty(sId);
},
```

**Effort:** 30 minutes (BaseController + 3 detail controllers)
**Risk:** Very Low — additive validation only

**Security note:** This does not replace backend authorization — it's defense-in-depth against obviously malformed IDs reaching the backend.

---

### Solution 3: Wrap LinkageDetail sub-calls in Promise.all

**Before (inferred pattern):**
```js
.then(function (oLinkage) {
  oVM.setProperty("/linkage", oLinkage);
  return SomeService.getById(oLinkage.orderId);  // sub-call 1
}).then(function (oOrder) {
  oVM.setProperty("/relatedOrder", oOrder);
  return AnotherService.getById(oLinkage.contractId);  // sub-call 2
}).catch(...);
```

**After:**
```js
.then(function (oLinkage) {
  oVM.setProperty("/linkage", oLinkage);
  return Promise.all([
    SomeService.getById(oLinkage.orderId),
    AnotherService.getById(oLinkage.contractId)
  ]);
}).then(function (aResults) {
  oVM.setProperty("/relatedOrder", aResults[0]);
  oVM.setProperty("/relatedContract", aResults[1]);
}).catch(function () {
  oVM.setProperty("/loading", false);
});
```

**Pros:** Both sub-calls still run concurrently (no regression); single error catch point; cleaner chain
**Effort:** 20 minutes
**Risk:** Very Low

## Recommended Action

1. **Solution 2 (UUID validation):** Implement immediately as a security-in-depth measure (30 min)
2. **Solution 3 (LinkageDetail Promise.all):** Implement immediately (20 min)  
3. **Solution 1 (_resolveLength):** Implement only if todo 008 is deferred; if todo 008 is done, this refactor is superseded

## Technical Details

**Affected files:**
- `webapp/controller/BaseController.js` — add `_resolveLength` (if needed) and `_isValidId`
- `webapp/controller/Home.controller.js` — use `_resolveLength` (if needed)
- `webapp/controller/CounterpartyDetail.controller.js` — add UUID validation in `_onRouteMatched`
- `webapp/controller/OrderDetail.controller.js` — add UUID validation in `_onRouteMatched`
- `webapp/controller/LinkageDetail.controller.js` — wrap sub-calls in `Promise.all`; add UUID validation

**UUID regex note:** The pattern `/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i` covers UUID v4 and other standard UUID versions. If IDs are numeric (integer PKs), also allow `/^\d+$/`.

**Database changes:** No

## Acceptance Criteria

- [ ] `_resolveLength` is not duplicated 3× in `Home._loadKpis` (either extracted or removed via todo 008)
- [ ] Navigating to `/counterparty/not-a-uuid` redirects to "not found" page (or shows error) rather than hitting the API
- [ ] Navigating to `/order/not-a-uuid` same behavior
- [ ] `LinkageDetail` sub-calls are wrapped in `Promise.all` with a single `.catch()` handler
- [ ] LinkageDetail view loads correctly for valid IDs (no regression)
- [ ] No `_isValidId` false-positives on valid IDs in the test suite

## Work Log

### 2025-01-31 - Discovered in code-simplicity, security, and performance review

**By:** code-simplicity-reviewer agent + security-sentinel agent + performance-oracle agent

**Actions:**
- code-simplicity-reviewer: identified `_resolveLength` 3× duplication as P1 simplicity finding
- security-sentinel: flagged route parameters not validated as UUIDs (P3 finding)
- performance-oracle: confirmed LinkageDetail sub-calls are already parallel but lack unified error handling
- Grouped into single todo since all 3 are in the "code quality" tier
