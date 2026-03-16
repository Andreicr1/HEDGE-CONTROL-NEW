---
status: complete
priority: p2
issue_id: "010"
tags: [code-review, backend, websocket]
dependencies: []
---

# Backend cancel action does not broadcast WS event

## Problem Statement

`RFQService.cancel()` modifies RFQ state but does not call `manager.broadcast()`. Other connected clients viewing the same RFQ will not receive a real-time `status_changed` event when an RFQ is cancelled.

## Findings

**Location**: `backend/app/services/rfq_service.py` — cancel method, `backend/app/api/routes/rfqs.py` — cancel endpoint

Other state transitions (award, reject) presumably broadcast. Cancel is inconsistent.

## Proposed Solutions

### Option A: Add broadcast to cancel endpoint
After successful cancel, broadcast `status_changed` event via `manager.broadcast()`.

- **Effort**: Small
- **Risk**: None

## Acceptance Criteria
- [ ] Cancel action broadcasts WS event
- [ ] Other connected clients see real-time status update

## Work Log
- 2026-03-16: Identified by architecture reviewer during PR #2 review
