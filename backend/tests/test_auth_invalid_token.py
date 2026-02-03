from fastapi import status

from app.core.auth import get_current_user
from app.main import app


def test_auth_invalid_token_returns_401(client) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    response = client.get(
        "/exposures/commercial",
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED