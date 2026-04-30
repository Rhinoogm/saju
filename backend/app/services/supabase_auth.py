from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from supabase import Client, create_client

from app.config import Settings, get_settings


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None = None
    role: str | None = None
    aud: str | None = None


class SupabaseAuthVerifier:
    def __init__(self, *, supabase_url: str, supabase_anon_key: str, expected_audience: str) -> None:
        self._supabase_url = supabase_url
        self._supabase_anon_key = supabase_anon_key
        self._expected_audience = expected_audience
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = create_client(self._supabase_url, self._supabase_anon_key)
        return self._client

    def verify(self, token: str) -> CurrentUser:
        response = self.client.auth.get_claims(token)
        if response is None:
            raise ValueError("Token has no claims")
        raw_claims = getattr(response, "claims", response)
        claims = _as_dict(raw_claims)
        user_id = claims.get("sub")
        if not isinstance(user_id, str) or not user_id:
            raise ValueError("Token has no subject")
        aud = claims.get("aud")
        if isinstance(aud, list):
            audience_ok = self._expected_audience in aud
            aud_value = ",".join(str(item) for item in aud)
        else:
            audience_ok = aud == self._expected_audience
            aud_value = aud if isinstance(aud, str) else None
        if not audience_ok:
            raise ValueError("Token audience is not accepted")
        role = claims.get("role")
        if role is not None and role != "authenticated":
            raise ValueError("Token role is not authenticated")
        email = claims.get("email")
        return CurrentUser(
            id=user_id,
            email=email if isinstance(email, str) else None,
            role=role if isinstance(role, str) else None,
            aud=aud_value,
        )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return dumped
    if hasattr(value, "dict"):
        dumped = value.dict()
        if isinstance(dumped, dict):
            return dumped
    return dict(value)


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization")
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token.strip()


@lru_cache
def _cached_auth_verifier(supabase_url: str, supabase_anon_key: str, expected_audience: str) -> SupabaseAuthVerifier:
    return SupabaseAuthVerifier(
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        expected_audience=expected_audience,
    )


def get_auth_verifier(settings: Settings) -> SupabaseAuthVerifier:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Auth is not configured",
        )
    return _cached_auth_verifier(settings.supabase_url, settings.supabase_anon_key, settings.supabase_jwt_audience)


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    token = _extract_bearer_token(request)
    if settings.local_demo_enabled and token == settings.local_demo_bearer_token:
        return CurrentUser(
            id=settings.local_demo_user_id,
            email=settings.local_demo_email,
            role="authenticated",
            aud=settings.supabase_jwt_audience,
        )
    try:
        verifier = get_auth_verifier(settings)
        return verifier.verify(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
