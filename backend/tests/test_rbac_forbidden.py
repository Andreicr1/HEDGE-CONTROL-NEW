from fastapi import status

from app.core.auth import get_current_user
from app.main import app


def test_rbac_forbidden_returns_403(client) -> None:
    app.dependency_overrides[get_current_user] = lambda: {"roles": ["trader"]}
    response = client.get("/audit/events")
    assert response.status_code == status.HTTP_403_FORBIDDEN