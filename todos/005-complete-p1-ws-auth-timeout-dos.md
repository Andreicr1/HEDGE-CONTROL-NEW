---
status: complete
priority: p1
issue_id: "005"
tags: [code-review, security, websocket, backend]
dependencies: []
---

# WebSocket pre-auth phase has no timeout — DoS risk

## Problem Statement

After `ws.accept()`, the backend waits indefinitely for the first authentication message. A malicious client could open many connections without authenticating, exhausting server resources.

## Findings

**Location**: `backend/app/api/routes/ws.py:177-203`

After `manager.connect(ws)`, the server enters the message loop without any timeout for the first message.

## Proposed Solutions

### Option A: asyncio.wait_for with 10s timeout
```python
try:
    raw = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
except asyncio.TimeoutError:
    await ws.close(code=1008, reason="Authentication timeout")
    return
```

Also add a max connections limit to `ConnectionManager`.

- **Effort**: Small
- **Risk**: Low

## Acceptance Criteria
- [ ] Unauthenticated connections are closed after 10s
- [ ] Test verifies timeout behavior

## Work Log
- 2026-03-16: Identified by security sentinel during PR #2 review
