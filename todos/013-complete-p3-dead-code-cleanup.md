---
status: complete
priority: p3
issue_id: "013"
tags: [code-review, simplicity, dead-code]
dependencies: []
---

# Dead code: useCursorPagination, ApiError, @tanstack/virtual-core

## Problem Statement

Three pieces of code are unused YAGNI:
1. `useCursorPagination.svelte.ts` + test (132 lines) — zero imports from any route
2. `ApiError` class in `errors.ts` + test (100 lines) — zero imports outside test
3. `@tanstack/virtual-core` dependency + vite chunk rule — zero imports in src/

## Findings

Identified by simplicity reviewer + performance reviewer.

## Proposed Solutions

### Option A: Delete all three
Remove files and dependency. Re-add when actually needed.

- **Effort**: Small (15 minutes)
- **Risk**: None — no consumers

## Acceptance Criteria
- [ ] No unused composables, classes, or dependencies
- [ ] Tests still pass after removal

## Work Log
- 2026-03-16: Identified by simplicity reviewer during PR #2 review
