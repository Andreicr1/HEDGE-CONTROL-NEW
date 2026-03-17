---
status: complete
priority: p3
issue_id: "014"
tags: [code-review, websocket, race-condition]
dependencies: []
---

# WS store processes domain events before auth_ack + other minor WS issues

## Problem Statement

Multiple minor WS issues:
1. Domain events arriving before `auth_ack` are dispatched to handlers that assume auth is complete
2. Persistent "Real-time indisponivel" notification not dismissed on WS reconnect
3. Backend WS sequence counter is process-local (breaks in multi-worker)
4. No sequence gap detection despite `seq` field being present

## Findings

**Locations**: ws.svelte.ts:161-178, ws.svelte.ts:245, ws.py:32

## Proposed Solutions

Guard domain event dispatch with `status !== 'authenticated'`. Clear persistent notification on reconnect. Use Redis INCR for production sequence counter.

- **Effort**: Small (guard), Medium (Redis counter)
- **Risk**: Low

## Work Log
- 2026-03-16: Identified by race condition reviewer + architecture reviewer during PR #2 review
