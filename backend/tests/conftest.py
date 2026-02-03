import os
import sys

import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_ISSUER", "https://login.microsoftonline.com/e75d5f00-51bd-48c1-adb6-b5df988e2685/v2.0")
os.environ.setdefault("JWT_AUDIENCE", "api://1d998abb-bc8e-404c-8bec-727de859c8c4")
os.environ.setdefault("JWKS_URL", "https://login.microsoftonline.com/e75d5f00-51bd-48c1-adb6-b5df988e2685/discovery/v2.0/keys")

from app.core.auth import get_current_user
from app.core.database import engine, SessionLocal
from app.main import app
from app.models.base import Base
from app import models as _models


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: {
        "roles": ["trader", "risk_manager", "auditor"]
    }
    return TestClient(app)


@pytest.fixture()
def session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
