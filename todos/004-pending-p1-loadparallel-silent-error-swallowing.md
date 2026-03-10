---
status: done
priority: p1
issue_id: "004"
tags: [ui5, error-handling, auth, session, base-controller]
dependencies: []
---

# Fix loadParallel Silent Error Swallowing (401/403/Network Failures)

## Problem Statement

`BaseController.loadParallel` wraps multiple async service calls in `Promise.all` with **no error handling whatsoever**. Any rejected promise — whether from a 401 (session expired), 403 (access denied), 404, or network failure — propagates to an unhandled promise rejection. The user sees the view stuck in its loading state with no feedback. Session expiry is completely invisible: expired users see a frozen loading spinner, not a redirect to login.

## Findings

- `webapp/controller/BaseController.js` — actual `loadParallel` implementation:
  ```js
  loadParallel: function (aFns) {
    return Promise.all(aFns.map(function (fn) { return fn(); }));
  },
  ```
  No `.catch()`, no `Promise.allSettled` fallback, no error classification.

- Service implementations (e.g., `ContractsService.js`):
  ```js
  list: function () {
    return fetch("/api/contracts/").then(function (r) { return r.json(); });
  }
  ```
  Fetch does **not** throw on HTTP error status codes. Non-2xx responses must be explicitly checked with `r.ok`. Currently, `r.json()` succeeds even on 401/403 responses (parsing the error body), but the downstream assignment `oVM.setProperty("/contracts", aResults[0])` then receives an error object instead of an array.

- `Home.controller.js` `_loadKpis`: **no `.catch()`** — inherited problem
- `CounterpartyDetail.controller.js` `_loadCounterparty`:
  ```js
  .catch(function () { oVM.setProperty("/loading", false); });
  ```
  Has a catch, but it only hides the spinner — it doesn't classify the error or redirect on 401.

- Security implication: 401 errors (expired JWT/session) are invisible. Users believe the app is loaded when they are actually unauthenticated; any data mutation attempt will then fail with a confusing error.

## Proposed Solutions

### Option 1: Add error handling in BaseController.loadParallel (Recommended)

**Approach — Phase 1 (immediate, non-breaking):**

First, fix each service to throw on non-OK responses:
```js
// BaseController.js — add a shared fetch helper
_fetch: function (sUrl, oOptions) {
  return fetch(sUrl, oOptions).then(function (r) {
    if (!r.ok) {
      var oErr = new Error("HTTP " + r.status);
      oErr.status = r.status;
      throw oErr;
    }
    return r.json();
  });
},
```

Second, add error classification to `loadParallel`:
```js
loadParallel: function (aFns) {
  return Promise.all(aFns.map(function (fn) { return fn(); }))
    .catch(function (oErr) {
      if (oErr && oErr.status === 401) {
        // Session expired — redirect to login
        window.location.href = "/";
        return Promise.reject(oErr);
      }
      // Re-throw so each controller's .catch can handle it
      return Promise.reject(oErr);
    });
},
```

**Phase 2:** Ensure every caller of `loadParallel` has a `.catch()` that calls `this.showError(...)`.

**Pros:** Centralized; consistent behavior; 401 → redirect pattern
**Cons:** Requires service layer update to propagate HTTP errors correctly
**Effort:** 2-3 hours
**Risk:** Low — purely additive

---

### Option 2: Switch to Promise.allSettled with partial data display

**Approach:** Replace `Promise.all` with `Promise.allSettled`, check each result's `status`, display available data, show warning for failed items.

**Pros:** Resilient — page works with partial data
**Cons:** More complex downstream handling; service status codes still need to propagate
**Effort:** 4-6 hours
**Risk:** Medium — changes data flow in callers

---

### Option 3: Do nothing in BaseController, enforce .catch() in all callers

**Approach:** Code review rule: every `loadParallel` call must have `.catch()`. Lint rule or PR checklist item.

**Pros:** Most flexible; callers keep full control
**Cons:** Doesn't fix 401 redirect centrally; still misses `Home._loadKpis`
**Effort:** 1 hour to add caller `.catch()` calls
**Risk:** Very Low

## Recommended Action

**Immediate (30 min):** Apply Option 3 — add `.catch()` to `Home._loadKpis` (currently completely missing). Apply the same to any other bare `loadParallel` calls.

**Short-term (2-3 hrs):** Apply Option 1 — add the centralized 401 redirect in `loadParallel` and fix the fetch helper to throw on non-OK responses.

## Technical Details

**Affected files:**
- `webapp/controller/BaseController.js` — add `_fetch` helper; add `.catch()` to `loadParallel`
- `webapp/service/ContractsService.js` — use `_fetch` or add `r.ok` check
- `webapp/service/OrdersService.js` — same
- `webapp/service/CounterpartysService.js` — same
- `webapp/service/ExposuresService.js` — same
- `webapp/service/RfqsService.js` — same
- `webapp/controller/Home.controller.js` — add `.catch()` to `_loadKpis`

**Security classification:**
- OWASP A07: Identification and Authentication Failures — expired session produces invisible failure
- CWE-390: Detection of Error Condition Without Action

**Database changes:** No

## Acceptance Criteria

- [ ] `loadParallel` has a `.catch()` that redirects to `/` on HTTP 401
- [ ] All service `fetch` calls throw an Error on non-2xx responses (check `r.ok`)
- [ ] `Home._loadKpis` has a `.catch()` that shows `errLoadFailed` message
- [ ] After token expiry, navigating any page shows a clear redirect or "session expired" message — NOT a frozen spinner
- [ ] HTTP 403 is logged to browser console with the accessed resource URL
- [ ] No regression in normal (200 OK) data loading

## Work Log

### 2025-01-31 - Discovered in security and architecture review

**By:** security-sentinel agent + architecture-strategist agent

**Actions:**
- Confirmed `loadParallel` has no `.catch()` via source read
- Confirmed `Home._loadKpis` has no `.catch()` via source read
- Confirmed `CounterpartyDetail._loadCounterparty` has `.catch()` but it's non-functional for 401 classification
- Rated P1: Silent 401 = invisible session expiry; frozen UI for unauthenticated users
