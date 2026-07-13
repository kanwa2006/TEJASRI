"""AuthService behavior with in-memory fakes."""

import pytest

from tejasri.application.auth_service import AuthService
from tejasri.core.errors import AuthenticationError, ConflictError, ValidationError
from tejasri.domain.entities import UserRole
from tejasri.infrastructure.security.passwords import Argon2PasswordHasher
from tejasri.infrastructure.security.tokens import JwtTokenIssuer
from tests.unit.fakes import FakeTenantRepository, FakeUserRepository

PASSWORD = "a-long-and-valid-password"


@pytest.fixture
def auth() -> AuthService:
    return AuthService(
        tenants=FakeTenantRepository(),
        users=FakeUserRepository(),
        hasher=Argon2PasswordHasher(),
        tokens=JwtTokenIssuer("unit-test-secret-key-of-sufficient-length", access_token_minutes=5),
    )


async def test_register_creates_tenant_with_admin(auth: AuthService) -> None:
    result = await auth.register_tenant("Sunrise Clinic", "a@b.example", PASSWORD, "Dr. A")
    assert result.tenant.name == "Sunrise Clinic"
    assert result.user.role is UserRole.ADMIN
    assert result.user.tenant_id == result.tenant.tenant_id
    assert result.access_token


async def test_password_is_stored_hashed_not_plaintext(auth: AuthService) -> None:
    result = await auth.register_tenant("Clinic", "a@b.example", PASSWORD, "Dr. A")
    assert PASSWORD not in result.user.password_hash


async def test_short_password_is_rejected(auth: AuthService) -> None:
    with pytest.raises(ValidationError):
        await auth.register_tenant("Clinic", "a@b.example", "short", "Dr. A")


async def test_duplicate_tenant_name_conflicts(auth: AuthService) -> None:
    await auth.register_tenant("Clinic", "a@b.example", PASSWORD, "Dr. A")
    with pytest.raises(ConflictError):
        await auth.register_tenant("Clinic", "c@d.example", PASSWORD, "Dr. C")


async def test_login_returns_token_for_valid_credentials(auth: AuthService) -> None:
    await auth.register_tenant("Clinic", "a@b.example", PASSWORD, "Dr. A")
    result = await auth.login("a@b.example", PASSWORD)
    assert result.access_token
    assert result.user.email == "a@b.example"


async def test_login_rejects_wrong_password(auth: AuthService) -> None:
    await auth.register_tenant("Clinic", "a@b.example", PASSWORD, "Dr. A")
    with pytest.raises(AuthenticationError):
        await auth.login("a@b.example", "wrong-password-entirely")


async def test_login_rejects_unknown_email(auth: AuthService) -> None:
    with pytest.raises(AuthenticationError):
        await auth.login("nobody@example.com", PASSWORD)
