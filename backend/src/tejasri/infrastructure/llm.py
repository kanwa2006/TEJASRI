"""LLM provider adapters (ADR 0003: provider-agnostic, failover-capable).

Every adapter implements the domain LLMProvider protocol and raises
ExternalServiceError on failure so FailoverLLMProvider can move down the
chain. The LLM's only job in TEJASRI is to *explain* — deterministic
logic decides (ADR 0004) — so total LLM failure degrades gracefully to a
template explanation at the application layer, never to an outage.
"""

from typing import Any

import httpx

from tejasri.core.errors import ExternalServiceError
from tejasri.core.logging import get_logger
from tejasri.domain.interfaces import LLMProvider

log = get_logger(__name__)


class GeminiProvider:
    """Google Gemini via the REST API (free Flash tier)."""

    name = "gemini"
    _URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        # Missing keys surface in generate() so the failover chain still runs.
        self._api_key = api_key
        self._model = model

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        if not self._api_key:
            raise ExternalServiceError("GEMINI_API_KEY is not configured")
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
        ]
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    self._URL.format(model=self._model),
                    params={"key": self._api_key},
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"gemini request failed: {exc}") from exc
        if response.status_code != 200:
            raise ExternalServiceError(f"gemini returned {response.status_code}")
        payload: dict[str, Any] = response.json()
        try:
            text: str = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ExternalServiceError("gemini returned an unexpected payload") from exc
        return text


class OllamaProvider:
    """Local Ollama — the $0, fully offline generation fallback."""

    name = "ollama"

    def __init__(self, base_url: str, model: str = "llama3.2") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        body = {
            "model": self._model,
            "stream": False,
            "messages": [{"role": "system", "content": system}, *messages],
        }
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(f"{self._base_url}/api/chat", json=body)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"ollama request failed: {exc}") from exc
        if response.status_code != 200:
            raise ExternalServiceError(f"ollama returned {response.status_code}")
        payload: dict[str, Any] = response.json()
        content = payload.get("message", {}).get("content")
        if not isinstance(content, str):
            raise ExternalServiceError("ollama returned an unexpected payload")
        return content


class BedrockProvider:
    """AWS Bedrock via the Converse API. Dormant by default (no free tier);
    enabled by installing the aws extra and setting LLM_PROVIDER=bedrock."""

    name = "bedrock"

    def __init__(self, region: str, model: str = "anthropic.claude-3-haiku-20240307-v1:0") -> None:
        try:
            import boto3
        except ImportError as exc:
            raise ExternalServiceError(
                'boto3 not installed; install with: pip install -e ".[aws]"'
            ) from exc
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self._model = model

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        import asyncio

        def _invoke() -> str:
            response = self._client.converse(
                modelId=self._model,
                system=[{"text": system}],
                messages=[
                    {"role": m["role"], "content": [{"text": m["content"]}]} for m in messages
                ],
            )
            text: str = response["output"]["message"]["content"][0]["text"]
            return text

        try:
            return await asyncio.to_thread(_invoke)
        except Exception as exc:  # boto3 raises many client error types
            raise ExternalServiceError(f"bedrock request failed: {exc}") from exc


class FailoverLLMProvider:
    """Tries each provider in order; raises only if all fail."""

    def __init__(self, providers: list[LLMProvider]) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self._providers = providers
        self.name = "+".join(p.name for p in providers)

    async def generate(self, system: str, messages: list[dict[str, str]]) -> str:
        last: ExternalServiceError | None = None
        for provider in self._providers:
            try:
                return await provider.generate(system, messages)
            except ExternalServiceError as exc:
                log.warning("llm_failover", provider=provider.name, error=exc.message)
                last = exc
        raise last if last else ExternalServiceError("no LLM providers available")
