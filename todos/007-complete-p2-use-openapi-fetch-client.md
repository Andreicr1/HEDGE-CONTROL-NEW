---
status: complete
priority: p2
issue_id: "007"
tags: [code-review, architecture, typescript, duplication]
dependencies: []
---

# Raw fetch() everywhere instead of typed openapi-fetch client

## Problem Statement

12 route pages duplicate raw `fetch()` + auth header injection instead of using the existing `openapi-fetch` client at `$lib/api/client.ts`. This means: (1) auth middleware is bypassed (no auto-401 logout), (2) `ApiError` class is dead code, (3) `schema.d.ts` types provide no value, (4) `API_BASE` is duplicated in 8+ files.

## Findings

Identified by: TypeScript reviewer, architecture reviewer, simplicity reviewer (consensus across 3 agents).

**~90 lines of boilerplate** across 12 files. The `ApiError` class (48 lines) and `useCursorPagination` (47 lines) are dead code because nothing uses the client.

## Proposed Solutions

### Option A: Migrate all routes to openapi-fetch client
Generate proper schema.d.ts from backend, then replace all raw fetch() with `client.GET()`, `client.POST()` etc.

- **Effort**: Large (generates type safety across all routes)
- **Risk**: Medium — requires backend running for schema generation

### Option B: Extract shared apiFetch utility
Create `$lib/api/fetch.ts` with centralized auth + error handling. Lighter than full openapi-fetch migration.

- **Effort**: Medium
- **Risk**: Low

## Acceptance Criteria
- [ ] No raw `fetch()` calls with manual auth headers in route pages
- [ ] Single source of truth for API_BASE
- [ ] 401 responses handled consistently (auto-logout)

## Work Log
- 2026-03-16: Identified by 3 review agents during PR #2 review
