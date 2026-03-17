---
status: complete
priority: p1
issue_id: "006"
tags: [code-review, bug, frontend]
dependencies: []
---

# Market-data frontend path mismatch + missing ingest body

## Problem Statement

Two bugs in the market-data page:
1. Frontend calls `/market-data/westmetall/prices` but backend route is `/market-data/westmetall/aluminum/cash-settlement/prices` — returns 404
2. `triggerIngest()` sends no body but backend `CashSettlementIngestRequest` requires `settlement_date` — returns 422

## Findings

**Location**: `frontend-svelte/src/routes/(protected)/market-data/+page.svelte:24,39`

Both bugs affect UI users and API agents equally.

## Proposed Solutions

### Option A: Fix paths and add date param
1. Fix fetch URL to `/market-data/westmetall/aluminum/cash-settlement/prices`
2. Add `settlement_date` (default today) to ingest POST body

- **Effort**: Small (10 minutes)
- **Risk**: None

## Acceptance Criteria
- [ ] Market data page loads prices successfully
- [ ] Ingest trigger sends valid request body
- [ ] Both work against real backend

## Work Log
- 2026-03-16: Identified by agent-native reviewer during PR #2 review
