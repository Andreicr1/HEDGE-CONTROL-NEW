---
status: complete
priority: p1
issue_id: "002"
tags: [code-review, typescript, websocket]
dependencies: []
---

# isControlMessage type guard too permissive — shadows domain events

## Problem Statement

The `isControlMessage` guard in `ws-events.ts` only checks `typeof obj.type === 'string'`. Since it's checked before `isWsEvent` in the WS store, any message with a `type` field will be intercepted as a control message and never reach domain event handlers. A malformed or future WS event with a `type` property would be silently swallowed.

## Findings

**Location**: `frontend-svelte/src/lib/api/types/ws-events.ts:156-160`

```typescript
export function isControlMessage(value: unknown): value is WsControlMessage {
    if (typeof value !== 'object' || value === null) return false;
    const obj = value as Record<string, unknown>;
    return typeof obj.type === 'string';  // Too weak
}
```

Called in `ws.svelte.ts:161` before `isWsEvent` — creates shadowing risk.

## Proposed Solutions

### Option A: Validate against known type values
```typescript
const CONTROL_TYPES = new Set(['auth_ack', 'subscription_ack', 'subscription_error', 'error']);
return typeof obj.type === 'string' && CONTROL_TYPES.has(obj.type);
```

- **Effort**: Small (5 minutes)
- **Risk**: None

## Acceptance Criteria
- [ ] `isControlMessage` only matches known control message types
- [ ] Test updated to verify unknown `type` values are rejected

## Work Log
- 2026-03-16: Identified by TypeScript reviewer + architecture reviewer during PR #2 review
