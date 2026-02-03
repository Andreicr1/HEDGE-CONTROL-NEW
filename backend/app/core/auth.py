from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt


JWKS_CACHE_TTL_SECONDS = 300


@dataclass
class AuthSettings:
    issuer: str
    audience: str
    jwks_url: str


def get_auth_settings() -> AuthSettings:
    issuer = os.getenv("JWT_ISSUER")
    audience = os.getenv("JWT_AUDIENCE")
    jwks_url = os.getenv("JWKS_URL")
    if not issuer or not audience or not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT settings missing",
        )
    return AuthSettings(issuer=issuer, audience=audience, jwks_url=jwks_url)


class JWKSCache:
    def __init__(self) -> None:
        self._jwks: dict[str, Any] | None = None
        self._expires_at = 0.0

    def get(self, settings: AuthSettings) -> dict[str, Any]:
        now = time.time()
        if self._jwks is None or now >= self._expires_at:
            self._jwks = self._fetch_jwks(settings.jwks_url)
            self._expires_at = now + JWKS_CACHE_TTL_SECONDS
        return self._jwks

    @staticmethod
    def _fetch_jwks(jwks_url: str) -> dict[str, Any]:
        try:
            response = httpx.get(jwks_url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="JWKS unavailable",
            ) from exc


_jwks_cache = JWKSCache()


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    return parts[1]


def _select_jwk(jwks: dict[str, Any], kid: str | None) -> dict[str, Any]:
    keys = jwks.get("keys", [])
    for key in keys:
        if kid is None or key.get("kid") == kid:
            return key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token key")


def get_current_user(
    request: Request,
    settings: AuthSettings = Depends(get_auth_settings),
) -> dict[str, Any]:
    token = _extract_token(request)
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    jwks = _jwks_cache.get(settings)
    jwk = _select_jwk(jwks, header.get("kid"))

    try:
        payload = jwt.decode(
            token,
            jwk,
            algorithms=[header.get("alg", "RS256")],
            audience=settings.audience,
            issuer=settings.issuer,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return payload


def require_role(role: str):
    return require_any_role(role)


def require_any_role(*roles: str):
    def _dependency(user: dict[str, Any] = Depends(get_current_user)) -> None:
        user_roles = set(user.get("roles") or [])
        if not user_roles.intersection(set(roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return _dependency