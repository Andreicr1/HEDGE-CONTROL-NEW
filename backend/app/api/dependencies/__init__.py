"""
API dependency modules.

This package contains FastAPI dependencies injected via ``Depends()``.

Currently only ``audit`` lives here because it is a *route-level* dependency
(injected per-endpoint to record audit trail events).

Authentication dependencies (``get_current_user``, ``require_roles``) reside
in ``app.core.auth`` because they are *application-wide* concerns shared by
middleware, startup hooks, and routes alike.
"""

__all__ = [
    "audit",
]
