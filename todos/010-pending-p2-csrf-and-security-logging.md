---
status: done
priority: p2
issue_id: "010"
tags: [security, csrf, logging, auth, monitoring]
dependencies: ["004"]
---

# CSRF Verification and Security Event Logging

## Problem Statement

Two security hygiene items need verification and implementation:

1. **CSRF posture**: The API uses JWT bearer tokens or session cookies. If session cookies are used with default `SameSite` settings, the application may be vulnerable to Cross-Site Request Forgery. The current frontend and backend code does not visibly implement CSRF token validation or use the double-submit cookie pattern.

2. **Security event logging**: The frontend handles HTTP 401 and 403 responses silently. There are zero structured log entries emitted for authentication failures, authorization denials, or session expiry events. Security teams cannot detect credential stuffing, unauthorized access attempts, or privilege escalation from frontend signals.

## Findings

### CSRF

- `webapp/service/*.js`: All service calls use native `fetch()` with default options — no `X-CSRF-Token` header, no verification token in request body
- `backend/app/core/` and `backend/app/main.py`: CORS configuration and CSRF middleware status not confirmed from frontend review (requires backend inspection)
- SAP UI5 framework does not automatically add CSRF tokens for custom fetch calls (only for OData model calls)
- **Risk condition**: If backend uses cookie-based auth without `SameSite=Strict/Lax` and without CSRF token validation, any cross-origin form post or JavaScript `fetch()` from an attacker-controlled page can perform state-changing operations as an authenticated user

### Security Event Logging

- `webapp/controller/BaseController.js`: No structured `console.warn` or telemetry calls for auth errors
- `CounterpartyDetail.controller.js` `.catch()`: `oVM.setProperty("/loading", false)` — no logging
- `Home.controller.js`: No `.catch()` at all (see todo 004)
- Observable result: Zero client-side signals for:
  - `SESSION_EXPIRED` (401)
  - `ACCESS_DENIED` (403)
  - `RATE_LIMITED` (429)
  - `LOAD_FAILURE` (network error)

## Proposed Solutions

### Part A: CSRF Verification and Remediation

**Step 1: Audit backend (required before frontend changes)**

Check `backend/app/main.py` and middleware configuration:
- Does the app use sessions (`SessionMiddleware`) or JWT bearer tokens?
- Is `SameSite=Strict` or `SameSite=Lax` set on any session cookie?
- Is there any CSRF middleware (e.g., `starlette-csrf`, `fastapi-csrf-protect`)?

**If JWT bearer tokens (Authorization header) are used:**
- CSRF is mitigated by design — bearer tokens are not automatically sent cross-origin
- **No frontend changes needed** — document this conclusion

**If session cookies are used without SameSite=Strict:**
- Backend: Add CSRF middleware or enforce `SameSite=Strict` on session cookies
- Frontend: Add `X-CSRF-Token` header to all mutating requests (`POST`, `PUT`, `DELETE`):
  ```js
  // In BaseController._fetch (see todo 004):
  if (oOptions && ["POST","PUT","DELETE"].includes(oOptions.method)) {
    oOptions.headers = oOptions.headers || {};
    oOptions.headers["X-CSRF-Token"] = this._getCsrfToken();
  }
  ```

### Part B: Security Event Logging

**Add structured event emission to `loadParallel` catch handler (pairs with todo 004):**

```js
// In BaseController.loadParallel .catch():
.catch(function (oErr) {
  var iStatus = oErr && oErr.status;
  if (iStatus === 401) {
    console.warn("[SECURITY] SESSION_EXPIRED", { url: oErr.url, ts: Date.now() });
    // Future: send to App Insights / SIEM endpoint
    window.location.href = "/";
  } else if (iStatus === 403) {
    console.warn("[SECURITY] ACCESS_DENIED", { url: oErr.url, ts: Date.now() });
  } else if (iStatus === 429) {
    console.warn("[SECURITY] RATE_LIMITED", { url: oErr.url, ts: Date.now() });
  } else {
    console.error("[APP] LOAD_FAILURE", oErr);
  }
  return Promise.reject(oErr);
});
```

**Future integration point:** These console events are structured for easy capture by Application Insights JS SDK or a custom telemetry endpoint if instrumenting the frontend later.

## Recommended Action

1. **Immediately:** Inspect `backend/app/main.py` and document the auth mechanism (JWT vs. cookie). If JWT bearer tokens, document CSRF as mitigated.
2. **Immediately (pairs with todo 004):** Add the structured security event logging in `loadParallel`.
3. **If cookie auth:** Add CSRF middleware to backend before production deployment.

## Technical Details

**Files affected:**
- `backend/app/main.py` — audit middleware; potentially add CSRF middleware
- `backend/app/core/security.py` (or equivalent) — verify cookie SameSite settings  
- `webapp/controller/BaseController.js` — add security event logging in `loadParallel` catch

**OWASP references:**
- A01:2021 – Broken Access Control (403 events invisible)
- A05:2021 – Security Misconfiguration (CSRF token omission)
- A09:2021 – Security Logging and Monitoring Failures (zero event logging)

**Note:** This todo assumes the app runs in a security context where SIEM monitoring is desired. For a development/demo deployment, Part B (logging) is still valuable for debugging auth issues.

**Database changes:** No

## Acceptance Criteria

- [ ] Backend auth mechanism is documented (JWT bearer or session cookie)
- [ ] If session cookies: `SameSite=Strict` or `SameSite=Lax` is confirmed set, OR CSRF middleware is active
- [ ] Frontend `loadParallel` emits structured `console.warn("[SECURITY]...")` events for 401 and 403
- [ ] Log format includes at minimum: event type, URL, timestamp
- [ ] Session expiry (401) triggers redirect to login page
- [ ] Authorization denial (403) is logged but does not redirect
- [ ] No CSRF vulnerability confirmed (via backend audit or by JWT usage)

## Work Log

### 2025-01-31 - Discovered in security review

**By:** security-sentinel agent

**Actions:**
- Identified no `X-CSRF-Token` headers in any service fetch call
- Identified no structured security event logging in any controller
- Backend auth mechanism not yet audited from frontend codebase
- Rated P2: Active security concern pending backend verification; logging gap is unambiguous
