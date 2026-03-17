---
status: complete
priority: p1
issue_id: "004"
tags: [code-review, svelte, bug, performance]
dependencies: []
---

# $derived(() => ...) should be $derived.by(() => ...) in analytics pages

## Problem Statement

Three analytics pages use `$derived(() => { ... })` which returns a function, not the computed value. The template then calls `chartOptions()` on every access, defeating memoization and causing redundant computation on every render.

## Findings

**Locations**:
- `analytics/pnl/+page.svelte:30` — `let chartOptions = $derived(() => { ... })`
- `analytics/mtm/+page.svelte:28` — same pattern
- `analytics/what-if/+page.svelte:48` — same pattern

Correct pattern: `$derived.by(() => { ... })` which memoizes the result.

## Proposed Solutions

### Option A: Replace $derived with $derived.by
Change all three files: `$derived(() =>` → `$derived.by(() =>` and remove `()` from template access.

- **Effort**: Small (10 minutes)
- **Risk**: None — pure bugfix

## Acceptance Criteria
- [ ] All three analytics pages use `$derived.by`
- [ ] Template accesses `chartOptions` directly, not as function call
- [ ] Charts still render correctly

## Work Log
- 2026-03-16: Identified by TypeScript reviewer + performance reviewer during PR #2 review
