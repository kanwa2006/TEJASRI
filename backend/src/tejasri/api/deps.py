"""Dependency wiring — the composition root for request handling.

FastAPI dependencies construct application services from infrastructure
adapters. Tests override these to inject fakes.
"""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tejasri.application.auth_service import AuthService
from tejasri.application.patient_service import PatientService
from tejasri.core.config import get_settings
from tejasri.core.errors import AuthenticationError
from tejasri.domain.entities import AuthenticatedIdentity
from tejasri.infrastructure.db import Database
from tejasri.infrastructure.repositories.accounts import (
    CockroachTenantRepository,
    CockroachUserRepository,
)
from tejasri.infrastructure.repositories.patients import (
    CockroachAuditLog,
    CockroachPatientRepository,
)
from tejasri.infrastructure.security.passwords import Argon2PasswordHasher
from tejasri.infrastructure.security.tokens import JwtTokenIssuer

_bearer = HTTPBearer(auto_error=False)


def get_database(request: Request) -> Database:
    db: Database = request.app.state.database
    return db


def get_token_issuer() -> JwtTokenIssuer:
    settings = get_settings()
    return JwtTokenIssuer(
        secret_key=settings.jwt_secret_key,
        access_token_minutes=settings.jwt_access_token_minutes,
    )


def get_auth_service(
    db: Annotated[Database, Depends(get_database)],
    tokens: Annotated[JwtTokenIssuer, Depends(get_token_issuer)],
) -> AuthService:
    return AuthService(
        tenants=CockroachTenantRepository(db),
        users=CockroachUserRepository(db),
        hasher=Argon2PasswordHasher(),
        tokens=tokens,
    )


def get_patient_service(
    db: Annotated[Database, Depends(get_database)],
) -> PatientService:
    return PatientService(
        patients=CockroachPatientRepository(db),
        audit=CockroachAuditLog(db),
    )


def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    tokens: Annotated[JwtTokenIssuer, Depends(get_token_issuer)],
) -> AuthenticatedIdentity:
    if credentials is None:
        raise AuthenticationError("missing bearer token")
    user_id, tenant_id, role = tokens.verify(credentials.credentials)
    return AuthenticatedIdentity(user_id=user_id, tenant_id=tenant_id, role=role)
