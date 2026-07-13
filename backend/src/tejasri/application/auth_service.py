"""Authentication use cases: tenant onboarding and login."""

from dataclasses import dataclass

from tejasri.core.errors import AuthenticationError, ValidationError
from tejasri.domain.entities import Tenant, User, UserRole
from tejasri.domain.interfaces import (
    PasswordHasher,
    TenantRepository,
    TokenIssuer,
    UserRepository,
)

_MIN_PASSWORD_LENGTH = 12


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    tenant: Tenant
    user: User
    access_token: str


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User
    access_token: str


class AuthService:
    def __init__(
        self,
        tenants: TenantRepository,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenIssuer,
    ) -> None:
        self._tenants = tenants
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    async def register_tenant(
        self,
        tenant_name: str,
        admin_email: str,
        admin_password: str,
        admin_display_name: str,
    ) -> RegistrationResult:
        """Create a new tenant (clinic/org) with its first admin user."""
        self._validate_password(admin_password)
        tenant = await self._tenants.create(tenant_name.strip())
        user = await self._users.create(
            tenant_id=tenant.tenant_id,
            email=admin_email,
            password_hash=self._hasher.hash(admin_password),
            role=UserRole.ADMIN,
            display_name=admin_display_name.strip(),
        )
        token = self._tokens.issue(user.user_id, user.tenant_id, user.role)
        return RegistrationResult(tenant=tenant, user=user, access_token=token)

    async def login(self, email: str, password: str) -> LoginResult:
        user = await self._users.get_by_email(email)
        # Verify against a constant dummy hash when the user is unknown so
        # response timing does not reveal which emails are registered.
        if user is None:
            self._hasher.verify(password, _DUMMY_HASH)
            raise AuthenticationError("invalid email or password")
        if not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("invalid email or password")
        token = self._tokens.issue(user.user_id, user.tenant_id, user.role)
        return LoginResult(user=user, access_token=token)

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < _MIN_PASSWORD_LENGTH:
            raise ValidationError(f"password must be at least {_MIN_PASSWORD_LENGTH} characters")


# A valid Argon2id hash of a random throwaway string; only used to equalize
# login timing for unknown emails.
_DUMMY_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$"
    "c29tZXNhbHRzb21lc2FsdA$WCzD2gYRnPMhF1r6zA0eHu0Kf1MEcvUlLm+cxJdcOWY"
)
