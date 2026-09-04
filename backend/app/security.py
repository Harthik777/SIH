"""Local authentication and role enforcement for the private Sentinel profile.

The public SIH deployment contains synthetic evidence and deliberately runs in
``optional`` mode.  A private deployment can set ``SENTINEL_AUTH_MODE=required``
to require a signed bearer token for every API route except login and health.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Header, HTTPException

from .config import get_settings


JWT_ALGORITHM = "HS256"
JWT_ISSUER = "sentinel-local"
JWT_AUDIENCE = "sentinel-investigation-api"
ROLE_LEVEL = {"viewer": 10, "analyst": 20, "supervisor": 30, "demo": 30}


@dataclass(frozen=True)
class Principal:
    email: str
    role: str
    mode: str


def hash_password(password: str, *, iterations: int = 310_000) -> str:
    """Return a portable PBKDF2-SHA256 credential for offline deployments."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, plaintext: str, encoded: str | None) -> bool:
    if encoded:
        try:
            algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations),
            ).hex()
            return hmac.compare_digest(actual, expected_hex)
        except (TypeError, ValueError):
            return False
    return hmac.compare_digest(password, plaintext)


def authenticate(email: str, password: str) -> Principal | None:
    settings = get_settings()
    candidates = (
        (settings.supervisor_email, settings.supervisor_password, settings.supervisor_password_hash, "supervisor"),
        (settings.analyst_email, settings.analyst_password, settings.analyst_password_hash, "analyst"),
    )
    for configured_email, plaintext, encoded, role in candidates:
        email_valid = hmac.compare_digest(email.casefold(), configured_email.casefold())
        password_valid = _verify_password(password, plaintext, encoded)
        if email_valid and password_valid:
            return Principal(configured_email, role, "authenticated")
    return None


def issue_token(principal: Principal) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.token_ttl_minutes)
    token = jwt.encode(
        {
            "sub": principal.email,
            "role": principal.role,
            "iat": now,
            "exp": expires,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "jti": secrets.token_hex(16),
        },
        settings.secret_key,
        algorithm=JWT_ALGORITHM,
    )
    return token, expires


def decode_token(token: str) -> Principal:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
        email = str(payload["sub"])
        role = str(payload.get("role", "viewer"))
        if role not in ROLE_LEVEL:
            raise ValueError("Unknown role")
        return Principal(email, role, "authenticated")
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired access token") from exc


def resolve_principal(authorization: str | None, *, enforce: bool = True) -> Principal:
    settings = get_settings()
    if settings.public_demo:
        # Public competition builds expose only bundled synthetic evidence. Ignore
        # stale private tokens so an old browser session cannot lock out the demo.
        return Principal("public-demo@sentinel.local", "demo", "synthetic-public-demo")
    if authorization and authorization.startswith("Bearer "):
        return decode_token(authorization.removeprefix("Bearer ").strip())
    if settings.auth_mode == "optional" or not enforce:
        return Principal(settings.supervisor_email, "supervisor", "trusted-local")
    raise HTTPException(status_code=401, detail="Authentication required")


def get_principal(authorization: Annotated[str | None, Header()] = None) -> Principal:
    return resolve_principal(authorization)


def require_roles(*roles: str) -> Callable[[Principal], Principal]:
    minimum = min((ROLE_LEVEL[role] for role in roles), default=ROLE_LEVEL["viewer"])

    def dependency(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        if ROLE_LEVEL.get(principal.role, 0) < minimum:
            raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(roles)}")
        return principal

    return dependency
