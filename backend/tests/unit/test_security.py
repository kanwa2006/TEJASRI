"""Password hashing and token issuance behavior."""

import uuid

import pytest

from tejasri.core.errors import AuthenticationError
from tejasri.domain.entities import UserRole
from tejasri.infrastructure.security.passwords import Argon2PasswordHasher
from tejasri.infrastructure.security.tokens import JwtTokenIssuer

SECRET = "unit-test-secret-key-not-a-real-credential"


class TestArgon2PasswordHasher:
    def test_roundtrip(self) -> None:
        hasher = Argon2PasswordHasher()
        digest = hasher.hash("correct horse battery staple")
        assert hasher.verify("correct horse battery staple", digest)

    def test_wrong_password_fails(self) -> None:
        hasher = Argon2PasswordHasher()
        digest = hasher.hash("correct horse battery staple")
        assert not hasher.verify("wrong password", digest)

    def test_hashes_are_salted(self) -> None:
        hasher = Argon2PasswordHasher()
        assert hasher.hash("same input") != hasher.hash("same input")

    def test_garbage_hash_fails_closed(self) -> None:
        assert not Argon2PasswordHasher().verify("anything", "not-a-hash")


class TestJwtTokenIssuer:
    def test_roundtrip_preserves_claims(self) -> None:
        issuer = JwtTokenIssuer(SECRET, access_token_minutes=5)
        user_id, tenant_id = uuid.uuid4(), uuid.uuid4()
        token = issuer.issue(user_id, tenant_id, UserRole.COORDINATOR)
        assert issuer.verify(token) == (user_id, tenant_id, UserRole.COORDINATOR)

    def test_tampered_token_is_rejected(self) -> None:
        issuer = JwtTokenIssuer(SECRET, access_token_minutes=5)
        token = issuer.issue(uuid.uuid4(), uuid.uuid4(), UserRole.ADMIN)
        with pytest.raises(AuthenticationError):
            issuer.verify(token[:-2] + "xx")

    def test_expired_token_is_rejected(self) -> None:
        issuer = JwtTokenIssuer(SECRET, access_token_minutes=-1)
        token = issuer.issue(uuid.uuid4(), uuid.uuid4(), UserRole.ADMIN)
        with pytest.raises(AuthenticationError):
            issuer.verify(token)

    def test_wrong_secret_is_rejected(self) -> None:
        token = JwtTokenIssuer(SECRET, 5).issue(uuid.uuid4(), uuid.uuid4(), UserRole.ADMIN)
        with pytest.raises(AuthenticationError):
            JwtTokenIssuer("a-different-secret-key-entirely-and-long", 5).verify(token)

    def test_empty_secret_is_a_configuration_error(self) -> None:
        with pytest.raises(ValueError, match="JWT secret"):
            JwtTokenIssuer("", 5)
