---
status: complete
priority: p1
issue_id: "001"
tags: [code-review, race-condition, security, trading]
dependencies: []
---

# RFQ Detail Page Race Conditions (3 Critical)

## Problem Statement

The RFQ detail page (`rfq/[id]/+page.svelte`, 532 lines) has three race conditions that can cause a trader to award based on stale data or see phantom state from a previous RFQ. On a commodity trading desk where a single aluminium contract can be six figures, these are unacceptable.

## Findings

### 1. Award-while-quotes-arrive race
When a trader clicks "Award", `operationInFlight = true` but WS `quote_received` events still update `quotes` array and trigger `debouncedRankingFetch()`. The trader's UI shows quotes that arrived after the award decision.

**Location**: `rfq/[id]/+page.svelte` lines 113-126, 173-223

### 2. Concurrent `loadAll()` with no generation guard
`loadAll()` is called from `onMount`, `status_changed` handler, and every action's success path. Two concurrent invocations race — "last write wins but both writes are stale."

**Location**: `rfq/[id]/+page.svelte` lines 48-76

### 3. Ranking timer leaks on param change
`rfqId` is `$derived(page.params.id)`. SvelteKit reuses the component on same-route navigation (`/rfq/aaa` → `/rfq/bbb`). The `rankingDebounce` timer from the first RFQ may fire for the wrong RFQ.

**Location**: `rfq/[id]/+page.svelte` — `onMount`/`onDestroy` don't handle param changes

## Proposed Solutions

### Option A: Guard + Generation Counter + $effect teardown
1. Skip WS handlers when `operationInFlight` is true
2. Add generation counter to `loadAll()` — discard superseded results
3. Use `$effect` on `rfqId` for WS setup/teardown instead of `onMount`/`onDestroy`

- **Pros**: Comprehensive fix, addresses all three issues
- **Cons**: Requires refactoring the page's lifecycle management
- **Effort**: Medium
- **Risk**: Low — behavioral changes are all safety improvements

### Option B: Extract `useRfqBoard` composable
Extract all data-fetching, WS orchestration, and state management into a composable that handles lifecycle correctly.

- **Pros**: Also addresses the "fat route" architectural concern
- **Cons**: Larger refactor
- **Effort**: Large
- **Risk**: Low

## Acceptance Criteria
- [ ] WS events are buffered/skipped during in-flight mutations
- [ ] Only the most recent `loadAll()` applies its results
- [ ] Navigating between RFQ detail pages cleans up timers and WS handlers
- [ ] No stale ranking data visible after param change

## Work Log
- 2026-03-16: Identified by race condition reviewer during PR #2 review
