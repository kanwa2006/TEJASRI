"""JWT access tokens (HS256) carrying user, tenant, and role claims."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from tejasri.core.errors import AuthenticationError
from tejasri.domain.entities import UserRole

_ALGORITHM = "HS256"


class JwtTokenIssuer:
    """Implements domain TokenIssuer with signed, expiring JWTs."""

    def __init__(self, secret_key: str, access_token_minutes: int) -> None:
        if not secret_key:
            raise ValueError("JWT secret key must be configured (JWT_SECRET_KEY)")
        self._secret = secret_key
        self._lifetime = timedelta(minutes=access_token_minutes)

    def issue(self, user_id: uuid.UUID, tenant_id: uuid.UUID, role: UserRole) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "role": role.value,
            "iat": now,
            "exp": now + self._lifetime,
        }
        return jwt.encode(payload, self._secret, algorithm=_ALGORITHM)

    def verify(self, token: str) -> tuple[uuid.UUID, uuid.UUID, UserRole]:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[_ALGORITHM])
            return (
                uuid.UUID(payload["sub"]),
                uuid.UUID(payload["tenant_id"]),
                UserRole(payload["role"]),
            )
        except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
            raise AuthenticationError("invalid or expired token") from exc
