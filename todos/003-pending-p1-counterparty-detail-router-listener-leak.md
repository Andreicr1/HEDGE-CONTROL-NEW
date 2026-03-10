---
status: done
priority: p1
issue_id: "003"
tags: [ui5, router, memory-leak, counterparty-detail]
dependencies: []
---

# Fix CounterpartyDetail Router Listener Leak (onExit Empty Stub)

## Problem Statement

`CounterpartyDetail.controller.js` attaches a route pattern-matched listener in `onInit` but never detaches it. The `onExit` lifecycle hook exists as an empty stub (`onExit: function () {}`). Each navigation to the counterparty detail view registers a new `_onRouteMatched` listener. After **N** navigations, each subsequent route match triggers `_loadCounterparty` **N times**, multiplying API calls geometrically.

## Findings

- `webapp/controller/CounterpartyDetail.controller.js` `onInit`:
  ```js
  this.getRouter().getRoute("counterpartyDetail").attachPatternMatched(this._onRouteMatched, this);
  ```
- `webapp/controller/CounterpartyDetail.controller.js` `onExit` (the stub):
  ```js
  onExit: function () {}
  ```
- The `_onRouteMatched` handler calls `_loadCounterparty(sId)` which fires 3 parallel API requests (getById, listByCounterparty, listByCounterparty for exposures)
- SAP UI5 controller lifecycle: `onExit` is the designated place to clean up subscriptions; failure leaks the subscription until the view is destroyed (which may not happen in a single-page app scenario)
- Pattern: `OrderDetail.controller.js` must be checked for the same issue (likely same pattern)

## Proposed Solutions

### Option 1: Fix onExit to detachPatternMatched (Recommended)

**Approach:**
```js
onExit: function () {
  this.getRouter()
    .getRoute("counterpartyDetail")
    .detachPatternMatched(this._onRouteMatched, this);
},
```

**Why this works:** The pattern `attachPatternMatched(fn, ctx)` uses reference equality on both `fn` and `ctx`. Passing the same references to `detachPatternMatched` correctly removes only this listener.

**Pros:** One line fix; idiomatic UI5; zero architectural impact
**Cons:** None
**Effort:** 5 minutes
**Risk:** Very Low

---

### Option 2: Use `attachRouteMatched` without a context and use `once`

Not a correct fix — `attachPatternMatched` with a context is the recommended UI5 pattern. Do not attempt to use an anonymous function as it cannot be detached.

## Recommended Action

Apply Option 1 immediately. Also **audit `OrderDetail.controller.js`** and any other detail controllers for the same empty `onExit` stub.

## Technical Details

**Affected files:**
- `webapp/controller/CounterpartyDetail.controller.js` — fix `onExit`
- Check: `webapp/controller/OrderDetail.controller.js` — likely same pattern

**Symptom at runtime:** First navigation loads data once. Second navigation to any counterparty detail fires all 3 API calls **twice**. Third navigation fires them **three times**. This compounds on every navigation within the session.

**Memory impact:** Each listener holds a closure reference to `this` (the controller instance), preventing garbage collection of the stale controller if the view is cached.

**Database changes:** No

## Acceptance Criteria

- [ ] `CounterpartyDetail.onExit` calls `detachPatternMatched` with matching function reference and context
- [ ] After 5 consecutive navigations to different counterparty detail pages, the Network tab shows exactly 3 API calls per navigation (not cumulative multiples)
- [ ] `OrderDetail.controller.js` inspected; fix applied if same pattern exists
- [ ] Browser console shows no listener leak warnings
- [ ] No regression in data loading on first navigation

## Work Log

### 2025-01-31 - Discovered in architecture review

**By:** Architecture-strategist agent

**Actions:**
- Confirmed `onExit: function () {}` stub via source code read
- Confirmed `attachPatternMatched(this._onRouteMatched, this)` in `onInit`
- Rated P1: memory leak that multiplies API calls with each navigation session-wide
