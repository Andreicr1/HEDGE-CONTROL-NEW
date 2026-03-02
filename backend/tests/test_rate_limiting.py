"""
Tests for rate limiting (Item 1.2).

RATE_LIMIT_MUTATION is set to "5/minute" in conftest.py so that
sending 6 requests triggers a 429.  The autouse ``reset_rate_limiter``
fixture clears counters between tests to avoid cross-test interference.
"""

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SALES_ORDER_BODY = {
    "price_type": "fixed",
    "quantity_mt": 10.0,
}

_PURCHASE_ORDER_BODY = {
    "price_type": "fixed",
    "quantity_mt": 5.0,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_post_under_limit_succeeds(client: TestClient) -> None:
    """Requests within the rate limit are served normally."""
    resp = client.post("/orders/sales", json=_SALES_ORDER_BODY)
    assert resp.status_code == 201


def test_post_over_limit_returns_429(client: TestClient) -> None:
    """Exceeding the rate limit returns 429 with Retry-After header."""
    # Burn through the 5/minute quota (6th request should be rejected)
    for _ in range(5):
        client.post("/orders/sales", json=_SALES_ORDER_BODY)

    resp = client.post("/orders/sales", json=_SALES_ORDER_BODY)
    assert resp.status_code == 429
    body = resp.json()
    assert "detail" in body
    assert "Rate limit exceeded" in body["detail"]


def test_rate_limit_is_per_endpoint(client: TestClient) -> None:
    """Different endpoints have independent rate-limit counters."""
    # Burn 4 of the 5/minute budget on /orders/sales …
    for _ in range(4):
        client.post("/orders/sales", json=_SALES_ORDER_BODY)

    # … the /orders/purchase counter should still be fresh
    resp = client.post("/orders/purchase", json=_PURCHASE_ORDER_BODY)
    # Should succeed (201), NOT 429
    assert resp.status_code == 201


def test_get_endpoints_are_not_rate_limited_by_mutation(client: TestClient) -> None:
    """GET endpoints are not affected by the mutation rate-limit counter."""
    # Burn all 5 mutations on /orders/sales
    for _ in range(5):
        client.post("/orders/sales", json=_SALES_ORDER_BODY)

    # GET /health should still work
    resp = client.get("/health")
    assert resp.status_code == 200
