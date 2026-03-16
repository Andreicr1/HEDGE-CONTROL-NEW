---
title: "feat: Svelte Frontend Greenfield — Trading Desk for Hedge Control"
type: feat
status: active
date: 2026-03-16
deepened: 2026-03-16
origin: docs/brainstorms/2026-03-16-svelte-frontend-greenfield-brainstorm.md
---

# Svelte Frontend Greenfield — Trading Desk for Hedge Control

## Enhancement Summary

**Deepened on:** 2026-03-16
**Review agents used:** architecture-strategist, security-sentinel, performance-oracle, julik-frontend-races-reviewer, kieran-typescript-reviewer, code-simplicity-reviewer

### Key Improvements

1. **CRITICAL security fix discovered:** JWT algorithm confusion vulnerability in `backend/app/core/auth.py:129` — hardcode `algorithms=["RS256"]` immediately
2. **WebSocket auth redesigned:** first-message authentication replaces query-param token (eliminates token leakage in logs)
3. **Race condition patterns documented:** 17 specific race conditions identified with prevention code for each
4. **Scope reduced ~30%:** deferred Orders, Deals, Settings/Audit views; simplified dashboard; removed premature features (keyboard shortcuts, resizable panels, i18n, optimistic updates)
5. **TypeScript architecture defined:** typed WS events (discriminated union), ApiError hierarchy, ComposeOption for ECharts, runtime validation for WS messages

### Critical Security Findings (fix before any new code)

| # | Finding | Severity | Location | Fix |
|---|---------|----------|----------|-----|
| 1 | JWT algorithm confusion — backend trusts client-supplied `alg` header | **CRITICAL** | `backend/app/core/auth.py:129` | Hardcode `algorithms=["RS256"]` |
| 2 | Auth bypass when `JWT_ISSUER` is empty (default = all roles) | **HIGH** | `backend/app/core/auth.py:24-26` | Fail startup if empty in production |
| 3 | No CSP header in nginx | **HIGH** | `frontend/nginx.conf` | Add Content-Security-Policy |
| 4 | No HSTS header | **HIGH** | `frontend/nginx.conf` | Add Strict-Transport-Security |
| 5 | CORS allows wildcard methods/headers | **MEDIUM** | `backend/app/main.py:138-144` | Restrict to actual methods |

---

## Overview

Greenfield SvelteKit SPA frontend replacing the SAP UI5 frontend entirely. Consumes the existing FastAPI backend (17 route modules, 60+ endpoints, JWT auth). Built as a trading desk — high information density, real-time RFQ lifecycle via WebSocket, dark mode default.

Zero reaproveitamento do UI5. O contrato de dados é a API REST do backend. A UX é reconstruída do zero.

(see brainstorm: `docs/brainstorms/2026-03-16-svelte-frontend-greenfield-brainstorm.md`)

## Problem Statement

SAP UI5/Fiori imposes structural limitations incompatible with commodity trading:

1. **RFQ lifecycle** — no primitives for real-time state. Polling at 10s intervals creates cognitive latency in time-sensitive decisions
2. **Data grids** — `sap.ui.table.TreeTable` lacks virtualization, flexible grouping, and conditional highlighting needed for cashflow/exposure views with 500+ rows
3. **Charts** — VizFrame is frozen in time. No brush selection, zoom, crosshair sync, or interactive what-if visualization
4. **Layout** — Fiori shell + FCL is designed for ERP, not trading. No multi-view composition, no density control

Performance degradation is functionally equivalent to broken for a trading desk.

## Proposed Solution

SvelteKit SPA mode (Svelte 5 runes) with:
- **Bits UI headless** for accessible primitives (modal, dropdown, select, combobox)
- **Tailwind CSS v4** for design language, dark mode, trading-oriented density
- **TanStack Table** (via `@tanstack/table-core` + custom Svelte 5 adapter) for grids
- **ECharts 6** (via tree-shaken imports + `ComposeOption`) for interactive charts
- **Custom RFQ Board** with WebSocket real-time + Svelte stores
- **openapi-typescript + openapi-fetch** for type-safe API client

## Technical Approach

### Architecture

```
frontend-svelte/
├── src/
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts         # openapi-fetch with auth middleware
│   │   │   ├── errors.ts         # ApiError class, typed error handling
│   │   │   ├── schema.d.ts       # Generated from OpenAPI (DO NOT EDIT)
│   │   │   ├── types/            # Hand-written discriminated unions
│   │   │   │   ├── rfq-intent.ts # CommercialHedgeRfq | GlobalPositionRfq | SpreadRfq
│   │   │   │   └── ws-events.ts  # WsEvent discriminated union + type guards
│   │   │   └── services/         # Typed service wrappers (only where logic > forwarding)
│   │   ├── stores/               # Global Svelte 5 rune stores (.svelte.ts)
│   │   │   ├── auth.svelte.ts    # JWT token, roles, session expiry timer
│   │   │   ├── ws.svelte.ts      # WS connection, subscriptions, event dispatch
│   │   │   ├── notifications.svelte.ts  # Centralized toast/alert queue
│   │   │   └── theme.svelte.ts   # Dark mode (default)
│   │   ├── components/
│   │   │   ├── ui/               # Bits UI wrappers with Tailwind styling
│   │   │   ├── table/            # TanStack Table adapter + DataTable component
│   │   │   ├── chart/            # EChart wrapper, trading-theme, LinkedChartGroup
│   │   │   └── layout/           # StatusBar (WS status, user, env)
│   │   └── utils/                # Formatters, validators, constants
│   ├── routes/
│   │   ├── +layout.svelte        # Shell: nav, theme, WS init
│   │   ├── +layout.ts            # ssr = false
│   │   ├── +error.svelte         # Root error boundary
│   │   ├── (public)/
│   │   │   └── login/+page.svelte
│   │   ├── (protected)/
│   │   │   ├── +layout.svelte    # Auth guard here (not root)
│   │   │   ├── +page.svelte      # Dashboard
│   │   │   ├── rfq/
│   │   │   │   ├── +layout.svelte
│   │   │   │   ├── +page.svelte  # RFQ list
│   │   │   │   ├── [id]/
│   │   │   │   │   ├── +page.svelte  # RFQ trading board
│   │   │   │   │   └── +error.svelte # 404 handling
│   │   │   │   └── new/+page.svelte
│   │   │   ├── cashflow/+page.svelte
│   │   │   ├── exposures/+page.svelte
│   │   │   ├── contracts/
│   │   │   │   ├── +page.svelte  # List
│   │   │   │   └── [id]/+page.svelte
│   │   │   ├── counterparties/
│   │   │   │   ├── +page.svelte
│   │   │   │   └── [id]/+page.svelte
│   │   │   ├── analytics/
│   │   │   │   ├── +layout.svelte  # Shared filters (date range, commodity)
│   │   │   │   ├── pnl/+page.svelte
│   │   │   │   ├── mtm/+page.svelte
│   │   │   │   └── what-if/+page.svelte
│   │   │   └── market-data/+page.svelte
│   │   app.css
│   │   └── app.html
├── static/
├── svelte.config.js
├── vite.config.ts                # Manual chunk splitting for ECharts, TanStack
├── tailwind.css
├── tsconfig.json
├── package.json
└── Dockerfile
```

### Research Insights: Architecture

**Route groups prevent auth redirect loop.** The root `+layout.svelte` is the shell (nav, theme, WS status) but does NOT contain the auth guard. Auth guard lives in `(protected)/+layout.svelte`. Login page lives in `(public)/`. This avoids the redirect loop where the auth guard fires before the login page loads.

**Analytics split into nested routes.** `/analytics/pnl`, `/analytics/mtm`, `/analytics/what-if` as separate routes with a shared layout. This gives automatic code splitting per sub-view — the What-If tab's ECharts import does not load until the user navigates there.

**`+error.svelte` at key levels.** Root error boundary catches unexpected failures. `rfq/[id]/+error.svelte` handles 404 when navigating to an invalid RFQ.

### Version Pinning

| Package | Version | Notes |
|---------|---------|-------|
| `svelte` | `^5.53` | Runes API stable |
| `@sveltejs/kit` | `^2.55` | SPA mode via adapter-static |
| `@sveltejs/adapter-static` | latest | `fallback: '200.html'` |
| `bits-ui` | `^2.16` | Svelte 5 headless, 50+ components |
| `tailwindcss` | `^4.2` | CSS-first config, dark mode native |
| `@tailwindcss/postcss` | latest | PostCSS plugin |
| `@tanstack/table-core` | `^8.21` | Core only — `@tanstack/svelte-table` broken with Svelte 5 |
| `@tanstack/virtual-core` | latest | `@tanstack/svelte-virtual` also broken — use core directly |
| `echarts` | `^6.0` | Tree-shakeable via `echarts/core` + `ComposeOption` |
| `openapi-typescript` | `^7.13` | Dev dependency, type generation |
| `openapi-fetch` | latest | Type-safe fetch client with middleware |

**Risk: TanStack Table.** Official Svelte 5 adapter ships with v9 (alpha). Use `@tanstack/table-core` + custom ~100-line adapter (copy from [svelte5-tanstack-table-reference](https://github.com/walker-tx/svelte5-tanstack-table-reference)). Write adapter tests in Phase 2 (not Phase 5). Migrate to v9 when stable.

### Vite Configuration (Performance-Critical)

```typescript
// vite.config.ts — manual chunk splitting
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('echarts')) return 'echarts';
          if (id.includes('@tanstack/table-core')) return 'tanstack-table';
          if (id.includes('@tanstack/virtual-core')) return 'tanstack-virtual';
        }
      }
    }
  }
});
```

Without this, Vite merges ECharts into the common chunk (shared between `/analytics/*` and `/market-data`), destroying the first-load budget.

### Implementation Phases

#### Phase 0: Foundation (scaffold + infra)

**Goal:** SvelteKit project bootstrapped, deployed, consuming backend API with type safety. Security fixes applied.

**Pre-requisite: Security fixes (before any new code):**

- [x] `backend/app/core/auth.py:129` — **CRITICAL:** Hardcode `algorithms=["RS256"]`
  ```python
  # BEFORE (vulnerable):
  algorithms=[header.get("alg", "RS256")]
  # AFTER (fixed):
  algorithms=["RS256"]
  ```
- [x] `backend/app/core/auth.py` — Add production startup check: fail if `JWT_ISSUER` is empty and `AUTH_DISABLED` is not explicitly set
- [x] `backend/app/main.py:138-144` — Restrict CORS methods and headers:
  ```python
  allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
  allow_headers=["Authorization", "Content-Type", "X-Trace-Id"],
  ```

**Tasks:**

- [x] `frontend-svelte/` — Initialize SvelteKit project with Svelte 5, TypeScript, adapter-static
  - `svelte.config.js`: adapter-static with `fallback: '200.html'`
  - `src/routes/+layout.ts`: `export const ssr = false;`
- [x] Tailwind CSS v4 setup
  - `tailwind.css` with CSS-first config, dark mode via class strategy
  - `@theme` block with trading tokens: `--color-surface`, `--color-accent`, `--color-danger`, `--color-success`
  - **Measure Tailwind output size early.** If > 25KB gzipped, audit for unused utilities.
- [x] OpenAPI type generation + CI drift detection strategy
  - npm script: `"api:types": "openapi-typescript http://localhost:8000/openapi.json -o src/lib/api/schema.d.ts"`
  - Commit generated `schema.d.ts` to git
  - **CI strategy:** Backend PRs that change routes/schemas MUST regenerate `schema.d.ts` as part of their CI pipeline. The backend CI job: (1) starts the backend, (2) runs `npx openapi-typescript http://localhost:8000/openapi.json -o /tmp/schema.d.ts`, (3) diffs against committed `frontend-svelte/src/lib/api/schema.d.ts`. If diff is non-empty, the backend PR **fails** with message: "API schema changed — run `npm run api:types` in frontend-svelte/ and commit the updated schema.d.ts". This ensures the feedback loop is complete: backend changes force frontend type updates in the same PR or a linked PR.
- [x] API client (`src/lib/api/client.ts`)

  ```typescript
  import createClient from 'openapi-fetch';
  import type { paths } from './schema';
  import { authStore } from '$lib/stores/auth.svelte';

  export const client = createClient<paths>({
    baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
  });

  client.use({
    async onRequest({ request }) {
      const header = authStore.getAuthHeader();
      if (header) request.headers.set('Authorization', header);
      return request;
    },
    async onResponse({ response }) {
      if (response.status === 401) {
        authStore.logout(); // layout guard handles redirect
      }
      return response;
    },
  });
  ```

- [x] API error types (`src/lib/api/errors.ts`)

  ```typescript
  interface ApiErrorSimple { detail: string; }
  interface ApiErrorValidation { detail: Array<{ loc: (string | number)[]; msg: string; type: string }>; }
  type ApiErrorBody = ApiErrorSimple | ApiErrorValidation;

  class ApiError extends Error {
    constructor(readonly status: number, readonly body: ApiErrorBody) { ... }
    isValidation(): boolean { return Array.isArray(this.body.detail); }
    isConflict(): boolean { return this.status === 409; }
  }
  ```

- [x] Auth store (`src/lib/stores/auth.svelte.ts`)
  - Class-based Svelte 5 store with `$state` runes
  - **Memory-only JWT** (reload = re-login for MVP)
  - `isAuthenticated` via `$derived`
  - Role extraction from JWT claims (`trader`, `risk_manager`, `auditor`)
  - **Session expiry warning:** decode `exp` claim, set timer for 5min before expiry, show "Session expires soon — re-authenticate" modal. Silent logout on a trading desk is operationally dangerous.
  - **Single-flight redirect:** boolean gate prevents multiple 401s from triggering multiple `goto('/login')` calls

  ```typescript
  type UserRole = 'trader' | 'risk_manager' | 'auditor';
  class AuthStore {
    private token = $state<string | null>(null);
    private claims = $state<JwtClaims | null>(null);
    readonly isAuthenticated = $derived(this.token !== null);
    readonly userRoles = $derived(this.claims?.roles ?? []);
    // ...
  }
  ```

- [x] Notifications store (`src/lib/stores/notifications.svelte.ts`)
  - Centralized toast queue for API errors, WS disconnects, rate limits, rollbacks
  - Root-level toast renderer in `+layout.svelte`
- [x] Root layout (`src/routes/+layout.svelte`)
  - Shell only: nav sidebar (collapsible), theme, WS status indicator
  - **Auth guard is NOT here** — lives in `(protected)/+layout.svelte`
- [x] Auth guard (`src/routes/(protected)/+layout.svelte`)
  - Redirect to `/login` if not authenticated
- [x] Login page (`src/routes/(public)/login/+page.svelte`)
  - JWT token input (manual paste for dev/staging, redirect to IdP for prod)
- [x] Docker + deployment
  - `Dockerfile`: Node build stage → Nginx runtime (**non-root**: use `nginxinc/nginx-unprivileged` or add user)
  - **Runtime config via JSON, not sed injection:**
    ```sh
    # docker-entrypoint.sh
    echo "{\"apiBaseUrl\": \"${VITE_API_BASE_URL}\"}" > /usr/share/nginx/html/config.json
    ```
  - `nginx.conf`: gzip, SPA fallback, **security headers:**
    ```nginx
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' wss: https:; img-src 'self' data: blob:; font-src 'self'; object-src 'none'; frame-ancestors 'self';" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
    ```
  - Update `docker-compose.yml`: add `frontend-svelte` service on port 5173
- [x] ECharts bundle size spike: import the 5 required chart types (line, bar, scatter, heatmap, custom) with tree-shaking. Verify gzipped size < 200KB. If exceeds, apply mitigations from Performance section.
- [x] Verify: app loads, authenticates, makes a typed API call (e.g., list counterparties), renders data

**Deliverable:** Deployed SvelteKit shell with auth, typed API client, security headers, and one working list view.

**Success criteria:**
- `npm run build` produces static assets
- Docker container serves the app with CSP/HSTS headers
- API calls are type-checked at compile time
- Auth flow works (login, session expiry warning, protected routes redirect)

---

#### Phase 1: RFQ Trading Board (P1 — most critical)

**Goal:** Full RFQ lifecycle with real-time WebSocket updates.

##### 1A: Backend — WebSocket Endpoint + Security Fixes

- [x] `backend/app/api/routes/ws.py` — WebSocket endpoint
  - **Endpoint:** `GET /ws` (global, not per-RFQ)
  - **Auth: First-message authentication** (NOT query param — avoids token leakage in logs):
    ```
    1. Client connects to /ws (no token in URL)
    2. Server accepts connection but marks as unauthenticated
    3. Client sends: {"action": "authenticate", "token": "<jwt>"}
    4. Server validates JWT (same JWKSCache as HTTP auth)
    5. If valid: mark connection as authenticated, proceed
    6. If invalid: close with 1008 (Policy Violation)
    7. Any message before authenticate → close with 1008
    ```
  - **Subscription model:** Client sends `{"action": "subscribe", "topic": "rfq", "id": "<rfq_id>"}` after auth. Server tracks subscriptions per connection.
  - **Subscription acknowledgment:** Server responds with `{"type": "subscription_ack", "topic": "rfq", "id": "<rfq_id>"}` or `{"type": "subscription_error", "topic": "rfq", "id": "<rfq_id>", "reason": "..."}`.
  - **Events pushed:** `quote_received`, `quote_updated`, `status_changed`, `invitation_delivered`, `invitation_failed`, `rfq_closed`
  - **Event format:** `{"event": "<type>", "rfq_id": "<uuid>", "data": {...}, "timestamp": "<iso>", "seq": <monotonic_int>}` — sequence number enables gap detection
  - **Connection manager:** async-compatible class (`asyncio.Lock`, not `threading.Lock`). Tracks active connections + subscriptions. Broadcast filters by subscription.
  - **Integration points:** RFQ service award/reject/refresh → `manager.broadcast()`. RFQ orchestrator → `manager.broadcast()` on quote creation.
  - **Token expiry:** Frontend proactively reconnects with fresh token before expiry. Backend does NOT re-validate after connect (MVP simplification — document this).
- [x] Middleware compatibility — extend `_StripApiPrefixMiddleware` in `main.py` to handle WebSocket scope for Azure SWA deployment
- [x] `backend/app/api/routes/rfqs.py` — Add missing transitions
  - CREATED → CLOSED and SENT → CLOSED (cancel action): `POST /rfqs/{rfq_id}/actions/cancel`
- [x] `backend/app/api/routes/rfqs.py` — Award response enhancement
  - Include `created_contract_ids: list[str]` in award response body
- [x] Fix N+1 query in RFQ list endpoint (lines 84-92): add `joinedload(RFQ.invitations)` to eliminate 50 extra queries per page load
- [x] Register WS route in `main.py`
- [x] Tests for WS endpoint (connection, first-message auth, subscribe/ack, event broadcast)

##### 1B: Frontend — WebSocket Infrastructure

- [x] WS event types (`src/lib/api/types/ws-events.ts`) — discriminated union:

  ```typescript
  interface QuoteReceivedEvent extends BaseWsEvent {
    event: 'quote_received';
    data: { quote_id: string; counterparty_id: string; fixed_price_value: number; ... };
  }
  // ... other event types ...
  type WsEvent = QuoteReceivedEvent | QuoteUpdatedEvent | StatusChangedEvent | ...;

  // Runtime type guard — MANDATORY. Never trust raw WS data.
  function isWsEvent(value: unknown): value is WsEvent { ... }
  ```

- [x] `src/lib/stores/ws.svelte.ts` — WebSocket manager (class-based Svelte 5 store)
  - `status`: `$state<'connecting' | 'open' | 'authenticated' | 'closed' | 'error'>('closed')`
  - **First-message auth:** after `onopen`, send `{"action": "authenticate", "token": "..."}`. Mark as `authenticated` only after server ack.
  - **Subscription buffer:** subscriptions requested before WS is authenticated are buffered and flushed on auth success
  - **Subscription registry:** `Map<string, {topic, id}>` — auto re-subscribes all active subscriptions on reconnect
  - **Typed event handlers:** `on<T extends WsEvent['event']>(eventType: T, handler: (event: WsEventMap[T]) => void): () => void`
  - **Reconnection:** exponential backoff (1s, 2s, 4s, cap at 30s), max 10 attempts then show manual reconnect button
  - **On reconnect:** re-authenticate → re-subscribe all active → full REST state refresh for subscribed RFQs
  - **No custom heartbeat.** Rely on "no message in 60s → trigger reconnect" as lightweight alternative. Avoids backend ping handler complexity.
  - **AbortError filter:** WS store must NOT feed AbortError into notification store
  - **Graceful degradation — polling fallback:** When WS status is `closed` or `error` for >5 seconds, automatically switch subscribed RFQs to REST polling at 5s interval. Show banner: "Real-time indisponível — atualizando via polling". On WS reconnection, cancel all polling timers and resume WS-driven updates. This prevents traders from being blind during WS outages — which is exactly the moment of highest operational stress.
    ```typescript
    // In ws.svelte.ts
    #pollingTimers = new Map<string, ReturnType<typeof setInterval>>();
    #degradationTimer: ReturnType<typeof setTimeout> | null = null;

    #onDisconnect() {
      this.#degradationTimer = setTimeout(() => {
        this.#startPollingFallback();
      }, 5000);
    }

    #onReconnect() {
      if (this.#degradationTimer) clearTimeout(this.#degradationTimer);
      this.#stopPollingFallback();
    }
    ```
- [x] Root layout integration
  - Initialize WS in `onMount` of root `+layout.svelte` when authenticated
  - Disconnect on logout / `onDestroy`
  - Show connection status in nav bar (green dot / yellow pulse / red X)
  - **Auth store logout also disconnects WS** (order: WS disconnect first, then clear tokens)

##### 1C: Frontend — RFQ List

- [x] `src/routes/(protected)/rfq/+page.svelte`
  - Table of active RFQs (state, commodity, direction, quantity, counterparty count, quote count, created_at)
  - Filter by state, intent, direction, commodity
  - Cursor-based pagination
  - **WS-driven badge updates:** on `quote_received` event, increment quote count client-side without re-fetching list. Full re-fetch only on WS reconnect.
  - Click row → navigate to `/rfq/[id]`
  - "New RFQ" button (trader role only)

##### 1D: Frontend — RFQ Creation

- [x] `src/routes/(protected)/rfq/new/+page.svelte`
  - Fields: commodity, quantity_mt, direction, intent, settlement month, counterparties (multi-select)
  - Counterparty picker with search, filter by type/KYC/sanctions
  - Preview WhatsApp text (POST `/rfqs/preview-text`) before submission
  - Spread intent: additional fields for buy_trade_id, sell_trade_id
  - Submit → POST `/rfqs` → navigate to `/rfq/[id]`

##### 1E: Frontend — RFQ Trading Board (the core component)

**Concurrency policy (design before coding):**

Define a formal state matrix for the board component:

| Board State | Allowed Actions | WS Events Accepted? | REST Calls Allowed? |
|------------|-----------------|---------------------|---------------------|
| IDLE | All (award, reject, refresh) | Yes — apply immediately | Yes |
| AWARDING | None | Deferred — HTTP response is authority | Blocked |
| REJECTING | None | Deferred | Blocked |
| RANKING_STALE | Award disabled, others allowed | Yes — but ranking re-fetch pending | Debounced ranking fetch |
| DISCONNECTED | Read-only | No (WS down) | Yes (with stale data warning) |

- [x] `src/routes/(protected)/rfq/[id]/+page.svelte` — RFQ detail with trading board
  - **Layout:** Fixed 3-column CSS Grid (`1fr 2fr 1fr`) — Invitations | Quotes + Ranking | Actions + Timeline. No resizable panels (defer until user feedback requests it).
  - **Per-RFQ state lives at page level** (not global store). Component `onMount` fetches via REST + subscribes to WS topic. `onDestroy` unsubscribes. Avoids stale state when navigating between RFQs.
  - **WS subscription in onMount with cleanup:**
    ```svelte
    onMount(() => {
      const unsub = wsStore.subscribe('rfq', data.rfqId);
      return unsub;
    });
    ```
  - **Header:** RFQ summary (commodity, qty, direction, state badge, created_at, counterparty count)
  - **Invitations panel:**
    - List with status (queued, sent, delivered, failed)
    - Failed = red highlight + "Retry" button
    - Real-time via WS `invitation_delivered` / `invitation_failed`
  - **Quotes panel:**
    - Table sorted by arrival time
    - New quotes: slide-in animation + highlight fade
    - Real-time via WS `quote_received` / `quote_updated`
  - **Ranking panel:**
    - Trade ranking (GET `/rfqs/{id}/trade-ranking`)
    - **Debounced re-fetch:** 300ms after last `quote_received`. AbortController cancels in-flight requests. Prevents 10 simultaneous ranking fetches during quote burst.
    - **Award disabled while ranking is stale** (between quote arrival and ranking re-fetch completion)

    ```typescript
    class RfqBoardState {
      #rankingController: AbortController | null = null;
      #rankingDebounce: ReturnType<typeof setTimeout> | null = null;
      #isRankingStale = $state(false);

      onQuoteReceived() {
        this.#isRankingStale = true;
        if (this.#rankingDebounce) clearTimeout(this.#rankingDebounce);
        this.#rankingDebounce = setTimeout(() => this.#fetchRanking(), 300);
      }

      async #fetchRanking() {
        this.#rankingController?.abort();
        this.#rankingController = new AbortController();
        try {
          const data = await api.GET('/rfqs/{rfq_id}/trade-ranking', {
            params: { path: { rfq_id: this.rfqId } },
            signal: this.#rankingController.signal,
          });
          this.ranking = data.data;
          this.#isRankingStale = false;
        } catch (e) {
          if (e instanceof DOMException && e.name === 'AbortError') return;
          throw e;
        }
      }
    }
    ```

  - **Actions panel (trader role):**
    - Award: **pessimistic** (loading spinner, wait for server response). Simpler and safer than optimistic for a high-stakes trading action.
    - On HTTP 409 (concurrent award): show "Already awarded by another user" + refresh state.
    - **Concurrent award guard:** On WS `status_changed` to AWARDED/CLOSED, disable all action buttons immediately. Banner: "RFQ closed by another user."
    - **Operation lock:** During in-flight mutation (award/reject), WS status_changed events are deferred. HTTP response is the authority.

    ```typescript
    onWsStatusChanged(event) {
      if (this.#operationInFlight) return; // HTTP response will handle it
      this.rfqState = event.data.to_state;
      this.disableAllActions();
    }
    ```

    - Reject quote: per-quote action
    - Reject entire RFQ
    - Cancel RFQ (new): CREATED/SENT → CLOSED
    - Refresh all invitations
  - **Timeline panel:**
    - State events (GET `/rfqs/{id}/state-events`) — vertical timeline
  - **State-dependent content** (single layout, conditionally populated panels — no layout switching):
    - CREATED: invitations + "Send" button, empty quotes/ranking
    - SENT: invitations + empty quotes (waiting)
    - QUOTED: full board
    - AWARDED/CLOSED: read-only with outcome summary, link to created contract

##### 1F: Frontend — RFQ Service Layer

- [x] `src/lib/api/services/rfq.ts` — only if it adds logic beyond forwarding to `openapi-fetch`
  - If service wraps WS subscription alongside REST (e.g., `getBoardState(rfqId)` fetches REST + subscribes WS), keep it
  - If service only maps `rfqService.list()` → `client.GET('/rfqs')`, remove it. Call typed client directly.

**Deliverable:** Complete RFQ lifecycle with real-time updates.

**Success criteria:**
- WebSocket authenticates via first message, reconnects automatically
- Quotes appear within 1s of backend processing
- Award creates contract and displays link
- Multiple traders on same RFQ: second award shows 409 + "already awarded" banner
- Connection loss shows visual indicator, reconnects, and refreshes state

---

#### Phase 2: Cashflow & Exposure Grids (P2)

**Goal:** TanStack Table-based grids with virtualization, grouping, and conditional highlighting.

##### 2A: TanStack Table Svelte 5 Adapter

- [x] `src/lib/components/table/create-table.svelte.ts` — Custom adapter

  ```typescript
  import { createTable, type TableOptions, type RowData } from '@tanstack/table-core';

  export function createSvelteTable<TData extends RowData>(options: TableOptions<TData>) {
    let resolvedOptions = $state({ ...options });
    let tableState = $state(resolvedOptions.initialState ?? {});

    const table = createTable({
      ...resolvedOptions,
      state: tableState,
      onStateChange: (updater) => {
        tableState = typeof updater === 'function' ? updater(tableState) : updater;
      },
    });

    $effect(() => {
      table.setOptions(prev => ({ ...prev, ...resolvedOptions, state: tableState }));
    });

    return table;
  }
  ```

  - **CRITICAL:** Use `$state` on table options only. Derive row model via `$derived`. Never put `table.getRowModel()` into `$state` (infinite reactivity loop).
  - `columnResizeMode: 'onEnd'` — prevents per-pixel row model recomputation
  - Support: sorting, filtering, grouping, expanding, pagination, column pinning, column visibility
  - **Write adapter tests in Phase 2** (not Phase 5)

- [x] `src/lib/components/table/DataTable.svelte` — Base table component (generic: `<script generics="TData">`)
  - Virtual rows via `@tanstack/virtual-core` (not `@tanstack/svelte-virtual`)
  - Virtual scroll overscan: 5-10 rows (prevents blank flashes during fast scroll)
  - Sticky header
  - Row selection, loading skeleton, empty state
  - **Column defs: prefer `accessorFn` over `accessorKey`** for type safety (accessorKey does not validate against `keyof TData`)

### Research Insights: TanStack Table Performance

- **500 rows flat + virtual scroll:** 60fps (trivial — only 20-30 rows in DOM)
- **500 rows + 3-level grouping + pinning:** 45-55fps (pinned columns = duplicate DOM)
- **Optimization:** Pre-compute conditional CSS classes in a `Map<rowId, string>` when data changes, not per-cell per-frame
- **Table data arrays:** Use `$state` at reference level only. Replace entire array on update, never mutate individual items. Avoids 12,500+ proxy traps for 500 rows × 25 fields.

##### 2B: Exposure Views

- [x] `src/routes/(protected)/exposures/+page.svelte`
  - Data: GET `/exposures/list` with cursor pagination
  - Grouping: by commodity, settlement_month, source_type
  - Pinned columns: commodity (left), status (right)
  - Conditional highlighting: `fully_hedged` green, `partially_hedged` amber, `open` red
  - Totalizadores per group
  - Net exposure summary: GET `/exposures/net` as header cards
  - **Data refresh while scrolling:** buffer updates, apply after 150ms scroll inactivity. Or show "Data updated — click to refresh" indicator.
- [x] Hedge tasks sub-view
  - GET `/exposures/tasks` — pending recommendations
  - "Create RFQ" on hedge_new tasks → pre-populates RFQ creation form

##### 2C: Cashflow Views

- [x] `src/routes/(protected)/cashflow/+page.svelte`
  - Tabbed: Analytics | Projections | Ledger
  - Analytics: date picker + hierarchical grid (contract → month → entries) + totalizadores
  - Projections: timeline bars by month
  - Ledger: flat table with filters, column pinning, inflows green / outflows red

##### 2D: Reusable Pagination Composable

- [x] `src/lib/composables/use-cursor-pagination.svelte.ts`
  - Handles cursor/next_cursor pattern
  - **Boolean guard:** refuse `loadMore()` while previous load is in-flight
  - Expose: `items`, `isLoading`, `hasMore`, `loadMore()`, `refresh()`

**Deliverable:** Cashflow and exposure views with hierarchical grouping, virtualization, and conditional highlighting.

**Success criteria:**
- Grid renders 500+ rows at 50-60fps scroll
- Grouping/ungrouping is instant
- Column pinning works with horizontal scroll
- Totalizadores update dynamically

---

#### Phase 3: Analytics / P&L / MTM (P3)

**Goal:** Interactive charts with ECharts — brush selection, zoom, crosshair sync, what-if scenarios.

##### 3A: ECharts Wrapper

- [x] `src/lib/components/chart/EChart.svelte` — Reactive wrapper

  ```svelte
  <script lang="ts">
    import { init, use, type ComposeOption } from 'echarts/core';
    import { CanvasRenderer, SVGRenderer } from 'echarts/renderers';
    import { LineChart, BarChart } from 'echarts/charts';
    import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components';
    import type { LineSeriesOption, BarSeriesOption } from 'echarts/charts';

    use([SVGRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent]);

    type TradingChartOption = ComposeOption<LineSeriesOption | BarSeriesOption | ...>;

    let { options, theme, style = 'width:100%;height:400px' }: Props = $props();
    // ... init in onMount, $effect for setOption, ResizeObserver ...
  </script>
  ```

  - **Use `SVGRenderer` for line/bar charts** (50KB memory vs 7.7MB for Canvas at 2x DPR). Use `CanvasRenderer` only for heatmap/scatter with large datasets.
  - **Use `ComposeOption`** (not generic `EChartsOption`) — catches missing chart type registrations at compile time
  - **Waterfall via stacked BarChart** (not CustomChart) — saves ~15KB from bundle
  - `onDestroy` → `chart.dispose()` — ECharts does NOT garbage-collect without explicit disposal
  - **ResizeObserver debounced** to every 2nd frame via `requestAnimationFrame`

- [x] `src/lib/components/chart/LinkedChartGroup.svelte.ts` — coordination store for linked charts

  ```typescript
  class LinkedChartGroup {
    #instances = $state(new Map<string, ECharts>());
    #expectedCount: number;
    constructor(expectedCount: number) { this.#expectedCount = expectedCount; }
    register(id: string, instance: ECharts) {
      this.#instances.set(id, instance);
      if (this.#instances.size === this.#expectedCount) {
        echarts.connect(Array.from(this.#instances.values()));
      }
    }
  }
  ```

- [x] `src/lib/components/chart/trading-theme.ts` — dark mode chart theme (embedded in EChart.svelte)

  ```typescript
  export const tradingDarkTheme = {
    color: ['#00c087', '#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6'],
    backgroundColor: 'transparent',
    textStyle: { color: '#94a3b8' },
  } satisfies Partial<ChartThemeColors>;
  ```

- [x] **Sanitize all user-generated strings** (counterparty names, messages) before passing to ECharts options. ECharts tooltips render HTML by default — XSS risk with untrusted data. Use plain text mode or escape `<>&"'`.

### Research Insights: ECharts Bundle Size

| Module | Est. gzipped |
|--------|-------------|
| echarts/core | ~18KB |
| SVGRenderer | ~22KB |
| Line + Bar + Scatter + Heatmap | ~42KB |
| Grid + Tooltip + Legend + DataZoom | ~44KB |
| **Base total** | **~126KB** |
| + BrushComponent (what-if only) | +14KB |
| + VisualMap (heatmap) | +8KB |
| **With all components** | **~148KB** |

Budget: < 200KB gzipped. **Achievable** with SVGRenderer and deferred Brush/Toolbox loading.

**Optimization:** Lazy-load BrushComponent + ToolboxComponent only when user navigates to What-If tab via dynamic import.

##### 3B: Analytics Routes (nested for code splitting)

- [x] `src/routes/(protected)/analytics/+layout.svelte` — shared tab navigation
- [x] `src/routes/(protected)/analytics/pnl/+page.svelte`
  - Waterfall chart (stacked bar): realized vs unrealized P&L
  - Deal-level breakdown table
- [x] `src/routes/(protected)/analytics/mtm/+page.svelte`
  - Line chart over time with contract-level breakdown
- [x] `src/routes/(protected)/analytics/what-if/+page.svelte` (risk_manager + auditor only)
  - Parameter inputs → POST `/scenario/what-if/run` → result in chart
  - Linked charts (original vs scenario) via LinkedChartGroup
  - **Lazy-load chart modules:** `{#await import('./WhatIfChart.svelte')}`
  - **Brush selection guard:** buffer data updates while user is mid-selection

##### 3C: Market Data View

- [x] `src/routes/(protected)/market-data/+page.svelte`
  - LME aluminum line chart + daily price table
  - Manual ingest trigger (risk_manager only)

**Deliverable:** Interactive analytics with linked charts and what-if visualization.

**Success criteria:**
- Charts respond within 100ms
- Crosshair sync between linked charts works
- What-if renders in < 2s
- Chart bundle < 200KB gzipped (measured)

---

#### Phase 4: Essential Supporting Views (scoped down)

**Goal:** Contracts and Counterparties (required by core trading flows). Dashboard.

**Deferred to Phase 5+ (not needed for core trading workflow):**
- Orders (SO/PO management — separate workflow, not gated by RFQ)
- Deals (Deal Engine backend still in progress — building view for unfinished backend is waste)
- Settings/Audit trail (low-frequency admin views)
- i18n (hardcode PT-BR; add Paraglide when EN support actually needed)

##### 4A: Dashboard (minimal)

- [x] `src/routes/(protected)/+page.svelte`
  - Active RFQ count by state (1 API call)
  - Latest pipeline run status (1 API call)
  - Quick action links: "New RFQ", "View Exposures", "View Analytics" (zero API calls)
  - **3 data sources, not 7.** Add widgets incrementally based on actual trader usage.

##### 4B: Contracts

- [x] `src/routes/(protected)/contracts/+page.svelte` — List with filters (status, classification, commodity)
- [x] `src/routes/(protected)/contracts/[id]/+page.svelte` — Detail: legs, settlement dates, linked orders/deals, MTM
- [x] Status transitions (activate, settle, cancel) — trader role

##### 4C: Counterparties

- [x] `src/routes/(protected)/counterparties/+page.svelte` — List with filters (type, KYC, sanctions)
- [x] `src/routes/(protected)/counterparties/[id]/+page.svelte` — Detail + CRUD

##### 4D: StatusBar

- [x] `src/lib/components/layout/StatusBar.svelte`
  - WS connection status, current user/role, environment indicator

**Deliverable:** Core trading workflow complete from dashboard through RFQ → contract → settlement.

---

#### Phase 5: Quality + Deployment

##### 5A: Testing

- [x] Unit tests: Vitest for stores, services, utilities
- [x] Component tests: Vitest + `@testing-library/svelte`
- [x] WebSocket tests: Mock WS server for store behavior (connect, auth, subscribe, reconnect, event dispatch)
- [x] E2E: Playwright for critical flows (RFQ creation → award → contract, login → dashboard)
- [x] API contract tests: CI runs `openapi-typescript`, diffs against committed `schema.d.ts`. Fail if changed.

##### 5B: CI/CD

- [x] GitHub Actions:
  - `npm run check` (svelte-check + TypeScript)
  - `npm run test`
  - `npm run build`
  - Schema drift detection (diff committed types)
  - Playwright E2E against docker-compose
- [x] Docker image build + push to ACR
- [x] Azure Container Apps deployment config

##### 5C: Performance Budget (revised)

| Metric | Target | Projected |
|--------|--------|-----------|
| Shell (first load JS) | < 180KB gz | 71-81KB (wide margin) |
| RFQ board chunk | < 150KB gz | 90-120KB |
| Table chunk (TanStack) | < 80KB gz | ~39KB |
| Chart chunk (ECharts) | < 200KB gz | ~148KB (with mitigations) |
| Grid scroll (500 rows + grouping) | 50fps+ | 45-60fps |
| WS reconnect | < 5s | 1-4s |
| What-if render | < 2s | 0.5-1.5s |

---

## Alternative Approaches Considered

| Approach | Why Rejected |
|----------|-------------|
| **Keep UI5, add Svelte micro-frontends** | Architectural costura — two frameworks, shared state problems, FCL layout still constrains |
| **React + Next.js** | Heavier runtime, virtual DOM overhead |
| **Svelte puro (no SvelteKit)** | Loses code splitting, layout nesting, routing |
| **SvelteKit with SSR** | Irrelevant for authenticated trading app |
| **Complete component library (Skeleton UI)** | SaaS aesthetic, customization attrition for trading density |
| **WS token in query param** | Token leaks to server logs, browser history, proxy logs. First-message auth is safer. |
| **Optimistic updates for award** | Rollback complexity not justified for infrequent, high-stakes action. Pessimistic is simpler and safer. |

## System-Wide Impact

### Interaction Graph

- Frontend → Backend REST API (60+ endpoints via openapi-fetch)
- Frontend → Backend WebSocket (`/ws` with first-message auth)
- Backend RFQ mutations → WS ConnectionManager.broadcast() → Frontend stores
- Backend WhatsApp webhook → RFQ Orchestrator → Quote creation → WS broadcast → Frontend
- Frontend auth store → JWT header injection → Backend auth middleware → Role enforcement

### Error Propagation

- **API errors:** openapi-fetch → `ApiError` class → centralized handler → notification store → toast
- **WS disconnect:** ws.svelte.ts → status change → UI indicator → auto-reconnect → re-auth → re-subscribe → REST refresh
- **Auth expiry:** session timer → warning modal (5min before) → redirect to login on expiry
- **Rate limit (429):** show toast notification. No automatic retry (2-service architecture, unlikely to hit limits under normal use).
- **AbortError:** filtered out, never shown to user

### State Lifecycle Risks

- **RFQ concurrent award:** Two users award same RFQ. Second gets HTTP 409. Frontend shows "Already awarded" banner. WS `status_changed` confirms to both users.
- **WS missed events:** Reconnection re-authenticates, re-subscribes, then does full REST refresh for all subscribed RFQs.
- **Stale ranking:** Debounced 300ms after last `quote_received`. Award disabled while ranking is stale. AbortController cancels in-flight ranking fetches.
- **Operation lock:** During in-flight mutation, WS events for that RFQ are deferred. HTTP response is the authority.
- **Multi-tab:** Each tab has own WS connection + auth state. Day-one: logout in one tab does NOT propagate (acceptable for MVP). Post-MVP: BroadcastChannel for auth sync.

### Integration Test Scenarios

1. **RFQ full lifecycle E2E:** Create RFQ → verify WS authenticates → simulate quote via webhook → verify quote appears → award → verify contract created → verify RFQ closed
2. **Concurrent trading:** Two browser sessions on same RFQ → one awards → verify other shows "already awarded" banner within 2s
3. **WS resilience:** Create RFQ → kill WS → simulate quote → restore WS → verify re-auth + re-subscribe → verify quote appears (via REST refresh)
4. **Auth flow:** Login → navigate → session expiry warning → re-login → verify return to previous route
5. **Grid performance:** Load 1000 exposures → scroll FPS > 50 → group by commodity → verify aggregation correct

## Acceptance Criteria

### Functional Requirements

- [ ] RFQ trading board shows real-time quote updates via WebSocket within 1s
- [ ] RFQ award creates contract and displays navigation link
- [ ] Concurrent award shows 409 banner, not silent failure
- [ ] Exposure grid supports grouping by 3+ dimensions with dynamic totalizadores
- [ ] Cashflow grid supports column pinning, virtual scrolling, conditional highlighting
- [ ] Charts support brush selection, zoom, and crosshair sync between linked panels
- [ ] What-if scenario renders within 2s
- [ ] Role-based UI: trader sees actions, risk_manager sees analytics, auditor sees audit trail
- [ ] Dark mode as default with correct contrast ratios (WCAG AA)
- [ ] All Bits UI primitives accessible via keyboard (Tab, Enter, Escape, Arrow keys)
- [ ] Session expiry warning 5 minutes before token expires

### Non-Functional Requirements

- [ ] Shell JS < 180KB gzipped
- [ ] Per-route chunks < 200KB gzipped
- [ ] Grid scroll at 50fps+ with 500+ rows (virtualized)
- [ ] WebSocket reconnect + re-auth + re-subscribe within 5s
- [ ] No runtime type errors from API responses (compile-time guarantee via openapi-typescript)
- [ ] CSP, HSTS, Permissions-Policy headers in production

### Quality Gates

- [ ] TypeScript strict mode, zero `any` in API layer
- [ ] Vitest coverage > 80% for stores and services
- [ ] Playwright E2E for all P1 flows (RFQ lifecycle)
- [ ] Zero svelte-check warnings in CI
- [ ] TanStack Table adapter has dedicated test suite

## Dependencies & Prerequisites

| Dependency | Phase | Status | Mitigation |
|-----------|-------|--------|------------|
| JWT algorithm fix (`auth.py:129`) | **Pre-Phase 0** | **CRITICAL vulnerability** | One-line fix, deploy immediately |
| Backend WebSocket endpoint (`/ws`) | Phase 1 | **Not implemented** | Build in Phase 1A |
| Backend: SENT → CLOSED transition | Phase 1 | **Not implemented** | Add in Phase 1A |
| Backend: award response with contract IDs | Phase 1 | **Not implemented** | Modify in Phase 1A |
| Backend: RFQ list N+1 query fix | Phase 1 | **Performance bug** | Add joinedload in Phase 1A |
| TanStack Table Svelte 5 adapter | Phase 2 | **Unstable** | table-core + custom adapter |
| `@tanstack/svelte-virtual` Svelte 5 | Phase 2 | **Broken** | Use virtual-core directly |
| Backend: Exposure Engine (P0) | Phase 2 | **In progress** | Design grid assuming exists; mock data if needed |
| Backend: Deal Engine (P0) | Deferred | **In progress** | Deal views deferred until engine ready |

## Risk Analysis & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| JWT algorithm confusion exploited before fix | **Critical** | Medium | Fix immediately — one-line change |
| TanStack Table v9 breaks custom adapter | Medium | Medium | Adapter is ~100 lines; migration straightforward |
| WebSocket scaling > 50 concurrent users | High | Low | In-process ConnectionManager; Redis pub/sub when needed |
| ECharts bundle exceeds 200KB | Medium | Low | SVGRenderer + deferred Brush/Toolbox = ~148KB projected |
| Svelte 5 breaking changes | Low | Low | Pin minor version |
| Backend P0 delayed | Medium | Medium | Mock data for frontend; connect when ready |

## Open Questions (from brainstorm, resolved)

| Question | Resolution |
|----------|-----------|
| Persistência de layout | **Fixed CSS Grid.** ResizablePanel deferred to post-MVP. |
| WS para outros módulos | **Deferred.** REST for cashflow/analytics. |
| i18n library | **Deferred.** Hardcode PT-BR. Add Paraglide when EN needed. |
| Estratégia de testes | **Vitest + Testing Library + Playwright** |
| Geração de tipos OpenAPI | **openapi-typescript** + committed schema + CI drift detection |
| WS auth mechanism | **First-message authentication** (not query param) |
| WS scope | **Global `/ws`** with subscription messages |
| Page reload auth | **Re-login.** Memory-only JWT. |
| Optimistic vs pessimistic | **Pessimistic for all mutations.** Simpler, safer for trading. |
| Dashboard content | **3 items:** RFQ counts, pipeline status, quick actions. |

## Future Considerations

- **ResizablePanel:** Add when traders request it. CSS Grid + pointer events + localStorage.
- **Keyboard shortcuts:** Add when traders request hotkeys. `1-9` for ranking, `R` for refresh.
- **Web Worker for what-if:** If > 100ms UI blocking in production, extract to worker.
- **Multi-tab sync:** BroadcastChannel for auth + WS events.
- **i18n:** Paraglide when EN support needed.
- **Mobile layout:** Not in scope. Trading desk is desktop-first.
- **RFQ human review queue:** Build when backend endpoint exists.
- **Orders/Deals/Settings views:** Phase 5+ when backend engines complete.

## Sources & References

### Origin

- **Brainstorm document:** [docs/brainstorms/2026-03-16-svelte-frontend-greenfield-brainstorm.md](../brainstorms/2026-03-16-svelte-frontend-greenfield-brainstorm.md)
  - Key decisions carried forward: SvelteKit SPA mode, Bits UI headless + Tailwind, TanStack Table, ECharts, WS for RFQ only, single global WS connection

### Internal References

- Backend API routes: `backend/app/api/routes/` (17 modules, 60+ endpoints)
- Pydantic schemas: `backend/app/schemas/` (15 schema files)
- RFQ service: `backend/app/services/rfq_service.py`
- RFQ orchestrator: `backend/app/services/rfq_orchestrator.py`
- Auth module (CRITICAL fix needed): `backend/app/core/auth.py:129`
- Integration audit (legacy bugs): `docs/integration-audit.md`
- Gap analysis: `docs/GAP_ANALYSIS_LEGACY_VS_NEW.md`

### External References

- [SvelteKit SPA mode](https://svelte.dev/docs/kit/single-page-apps)
- [Svelte 5 runes](https://svelte.dev/docs/svelte/$state)
- [Bits UI](https://bits-ui.com/docs/getting-started)
- [Tailwind CSS v4](https://tailwindcss.com/blog/tailwindcss-v4)
- [TanStack Table core](https://tanstack.com/table/latest/docs/installation)
- [Svelte 5 + TanStack Table adapter](https://github.com/walker-tx/svelte5-tanstack-table-reference)
- [ECharts 6](https://echarts.apache.org/)
- [svelte-echarts](https://github.com/bherbruck/svelte-echarts)
- [openapi-typescript](https://openapi-ts.dev/introduction)
- [openapi-fetch](https://openapi-ts.dev/openapi-fetch/)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)

### Review Agent Reports

- **Architecture Strategist:** Route group restructuring, WS middleware compatibility, token expiry handling, notification store, debounced ranking fetches
- **Security Sentinel:** 15 findings (1 critical, 4 high, 6 medium, 4 low). JWT algorithm confusion, WS auth redesign, CSP/HSTS headers, Docker non-root
- **Performance Oracle:** Bundle size projections, manual chunk splitting, N+1 query fix, $state reference-level usage, SVGRenderer recommendation, resize throttling
- **Frontend Races Reviewer:** 17 race conditions. WS subscription buffer, operation lock pattern, AbortController for ranking, single-flight redirect, scroll-aware data updates
- **TypeScript Reviewer:** WS event discriminated union, ApiError hierarchy, ComposeOption, generics attribute, runtime WS validation, accessorFn preference
- **Simplicity Reviewer:** Scope reduction ~30%. Deferred: ResizablePanel, keyboard shortcuts, i18n, Orders, Deals, Settings. Simplified: dashboard (3→7 sources), shell budget (180KB), pessimistic updates everywhere
