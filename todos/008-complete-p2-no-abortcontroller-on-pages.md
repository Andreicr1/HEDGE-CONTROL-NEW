---
status: complete
priority: p2
issue_id: "008"
tags: [code-review, race-condition, performance]
dependencies: []
---

# No AbortController on page-level data fetches

## Problem Statement

8+ route pages fire `fetch()` in `onMount` with no abort signal and no cancellation on unmount. Fast navigation wastes bandwidth and can set state on unmounted components. The `$effect(() => fetchCounterparties())` in rfq/new should be `onMount`.

## Findings

Identified by: race condition reviewer, performance reviewer.

**Affected pages**: exposures, cashflow, contracts, counterparties, analytics (pnl, mtm, what-if), market-data, rfq/new.

Only `rfq/[id]` uses AbortController (for ranking fetches).

## Proposed Solutions

### Option A: AbortController pattern on all pages
```typescript
let abortController: AbortController;
onMount(() => { abortController = new AbortController(); loadData(abortController.signal); });
onDestroy(() => { abortController?.abort(); });
```

Also change `$effect(() => fetchCounterparties())` → `onMount(() => fetchCounterparties())` in rfq/new.

- **Effort**: Small (per page)
- **Risk**: None

## Acceptance Criteria
- [ ] All page fetches use AbortController
- [ ] Navigation away cancels in-flight requests
- [ ] rfq/new uses onMount, not $effect

## Work Log
- 2026-03-16: Identified by 2 review agents during PR #2 review
