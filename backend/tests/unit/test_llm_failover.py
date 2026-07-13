"""FailoverLLMProvider: provider outages degrade, they do not break."""

import pytest

from tejasri.core.errors import ExternalServiceError
from tejasri.infrastructure.llm import FailoverLLMProvider


class FlakyProvider:
    def __init__(self, name: str, fail: bool) -> None:
        self.name = name
        self.fail = fail
        self.calls = 0

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        if self.fail:
            raise ExternalServiceError(f"{self.name} is down")
        return f"answer from {self.name}"


async def test_primary_success_never_touches_fallback() -> None:
    primary, fallback = FlakyProvider("primary", False), FlakyProvider("fallback", False)
    result = await FailoverLLMProvider([primary, fallback]).generate("s", [])
    assert result == "answer from primary"
    assert fallback.calls == 0


async def test_primary_failure_falls_over() -> None:
    primary, fallback = FlakyProvider("primary", True), FlakyProvider("fallback", False)
    result = await FailoverLLMProvider([primary, fallback]).generate("s", [])
    assert result == "answer from fallback"


async def test_total_outage_raises_external_service_error() -> None:
    chain = FailoverLLMProvider([FlakyProvider("a", True), FlakyProvider("b", True)])
    with pytest.raises(ExternalServiceError):
        await chain.generate("s", [])


def test_empty_chain_is_a_configuration_error() -> None:
    with pytest.raises(ValueError):
        FailoverLLMProvider([])
