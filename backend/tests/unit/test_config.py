"""Settings behavior tests."""

import pytest

from tejasri.core.config import Environment, LLMProviderName, Settings


def test_defaults_are_development_safe() -> None:
    settings = Settings(_env_file=None)
    assert settings.tejasri_env is Environment.DEVELOPMENT
    assert settings.llm_provider is LLMProviderName.GEMINI
    assert not settings.is_production


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEJASRI_ENV", "production")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    settings = Settings(_env_file=None)
    assert settings.is_production
    assert settings.llm_provider is LLMProviderName.OLLAMA


def test_secret_key_is_not_exposed_in_repr() -> None:
    settings = Settings(_env_file=None, jwt_secret_key="super-secret")
    assert "super-secret" not in repr(settings)
