"""Authentication endpoints: tenant registration and login."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from tejasri.api.deps import get_auth_service
from tejasri.application.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=120)
    admin_email: EmailStr
    admin_password: str = Field(min_length=12, max_length=256)
    admin_display_name: str = Field(min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — token scheme name, not a secret
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Create a tenant (clinic/org) with its first admin user."""
    result = await auth.register_tenant(
        tenant_name=body.tenant_name,
        admin_email=body.admin_email,
        admin_password=body.admin_password,
        admin_display_name=body.admin_display_name,
    )
    return AuthResponse(
        access_token=result.access_token,
        tenant_id=result.tenant.tenant_id,
        user_id=result.user.user_id,
        role=result.user.role.value,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    auth: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    result = await auth.login(email=body.email, password=body.password)
    return AuthResponse(
        access_token=result.access_token,
        tenant_id=result.user.tenant_id,
        user_id=result.user.user_id,
        role=result.user.role.value,
    )
