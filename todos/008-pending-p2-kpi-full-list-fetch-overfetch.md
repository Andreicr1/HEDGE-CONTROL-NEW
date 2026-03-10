---
status: done
priority: p2
issue_id: "008"
tags: [ui5, performance, api, kpi, overfetch, backend]
dependencies: ["007"]
---

# Replace Full-List KPI Fetches with Lightweight Count Endpoints

## Problem Statement

The Home dashboard KPI tiles for Orders, Contracts, and RFQs call `list()` methods that retrieve the full dataset payload, then immediately discard all record data and retain only `.length`. At 5,000 records per entity with an average of ~500 bytes per record, this wastes **~7.5MB of data per KPI refresh**. The user sees a count ("2,847") but the app transferred the equivalent of a small database dump to compute it.

## Findings

- `webapp/controller/Home.controller.js` `_loadKpis`:
  ```js
  this.loadParallel([
    function () { return exposuresService.getNet(); },
    function () { return ordersService.list(); },       // ← full payload, just for .length
    function () { return contractsService.list(); },    // ← full payload, just for .length
    function () { return rfqService.list(); },          // ← full payload, just for .length
  ]).then(function (aResults) {
    oVM.setProperty("/kpiOrdersCount",    Array.isArray(aResults[1]) ? aResults[1].length : "–");
    oVM.setProperty("/kpiContractsCount", Array.isArray(aResults[2]) ? aResults[2].length : "–");
    oVM.setProperty("/kpiRfqsCount",      Array.isArray(aResults[3]) ? aResults[3].length : "–");
  });
  ```
- **Performance projection at 5K records per entity:**
  - `ordersService.list()` → ~2.5MB
  - `contractsService.list()` → ~2.5MB
  - `rfqService.list()` → ~2.5MB
  - **Total: 7.5MB per KPI refresh**
- Additionally, this extends API response time: the backend must serialize the entire table rather than a single `SELECT COUNT(*)` query
- The existing `GET /api/orders/`, `GET /api/contracts/`, and `GET /api/rfqs/` endpoints return full record arrays — there are no `?count_only=1` or `HEAD` count variants

## Proposed Solutions

### Option 1: Add /count backend endpoints + lightweight service methods (Recommended)

**Backend changes (FastAPI):**
```python
# backend/app/api/orders.py
@router.get("/count", response_model=schemas.CountResponse)
async def get_orders_count(db: AsyncSession = Depends(get_db)):
    count = await db.scalar(select(func.count(Order.id)))
    return {"count": count}
```
Apply the same pattern to `/api/contracts/count` and `/api/rfqs/count`.

**Frontend service changes:**
```js
// webapp/service/OrdersService.js — add:
getCount: function () {
  return fetch("/api/orders/count").then(function (r) { return r.json(); });
}
```

**Home.controller.js update:**
```js
function () { return ordersService.getCount(); },     // { count: N }
// ...
oVM.setProperty("/kpiOrdersCount", aResults[1].count ?? "–");
```

**Pros:** ~7.5MB/refresh → ~150 bytes; backend query drops from O(n) scan to O(1) index
**Cons:** Requires backend changes; three new endpoints to add + test
**Effort:** 2-4 hours (backend) + 30 min (frontend)
**Risk:** Low

---

### Option 2: Use HTTP HEAD on existing list endpoint with Content-Range header

**Approach:** Backend adds `content-range: items 0-N/TOTAL` response header. Frontend makes `HEAD` request and reads the `Content-Range` header.

**Pros:** No additional endpoints; standard HTTP pattern
**Cons:** Not all backends support this cleanly; requires CORS header exposure for `Content-Range`; less developer-friendly
**Effort:** 2 hours backend + 1 hour frontend
**Risk:** Medium (CORS configuration)

---

### Option 3: Use query parameter `?limit=0&count=true`

**Approach:** Add `?count_only=true` query param to existing list endpoints that returns `{ count: N }` instead of records.

**Pros:** One endpoint per resource; same URL structure
**Cons:** Overloads the list endpoint contract; can cause confusion
**Effort:** 2 hours backend + 30 min frontend
**Risk:** Low

## Recommended Action

Apply **Option 1** — the dedicated `/count` endpoint pattern. It's the clearest API contract, the simplest to test, and the most idiomatic for a REST API. Add the endpoints to all three resources together with schema validation.

## Technical Details

**Backend files affected:**
- `backend/app/api/orders.py` — add `GET /count` route
- `backend/app/api/contracts.py` — add `GET /count` route
- `backend/app/api/rfqs.py` — add `GET /count` route
- `backend/app/schemas/` — add `CountResponse` schema (or reuse if exists)

**Frontend files affected:**
- `webapp/service/OrdersService.js` — add `getCount()`
- `webapp/service/ContractsService.js` — add `getCount()`
- `webapp/service/RfqsService.js` — add `getCount()`
- `webapp/controller/Home.controller.js` — update `_loadKpis` to call `getCount()` and unpack `.count`

**API response contract:**
```json
GET /api/orders/count → 200 { "count": 2847 }
GET /api/contracts/count → 200 { "count": 1203 }
GET /api/rfqs/count → 200 { "count": 456 }
```

**Note:** `exposuresService.getNet()` already returns a summary value (not a full list), so it is **not** affected by this issue.

**Database changes:** No schema changes. Each new endpoint runs `SELECT COUNT(*) FROM ...` — ensure indexed PK column is used.

## Acceptance Criteria

- [ ] `GET /api/orders/count`, `GET /api/contracts/count`, `GET /api/rfqs/count` return `{ "count": N }`
- [ ] `Home._loadKpis` no longer calls `.list()` on orders, contracts, or rfqs
- [ ] KPI counts display correctly on the Home dashboard
- [ ] Network tab shows KPI refresh transfers <1KB total (not >7.5MB)
- [ ] Backend tests cover the `/count` endpoints
- [ ] Service `getCount()` methods follow same pattern as existing service methods

## Work Log

### 2025-01-31 - Discovered in performance and security review

**By:** performance-oracle agent

**Actions:**
- Confirmed `_loadKpis` calls `.list()` on orders, contracts, rfqs and uses only `.length`
- Quantified 7.5MB waste at 5K records per entity per dashboard refresh
- Confirmed no count endpoints exist in backend API
- Rated P2: Performance and data overfetch; backend fix required; user-visible load time impact
