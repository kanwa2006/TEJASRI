"""Embedding providers (ADR 0003: local and deterministic by default).

Three implementations behind the domain EmbeddingProvider interface:

- HashingEmbedder    — dependency-free, fully deterministic token-hash
                       embedding. Default for dev/CI and the guaranteed
                       offline fallback. Token overlap ≈ similarity.
- SentenceTransformerEmbedder — real semantic embeddings via bge-small
                       (384-dim). Optional extra: `pip install -e ".[local-embeddings]"`.
- GeminiEmbedder     — hosted embeddings truncated to 384 dims. Synthetic
                       data only (ADR 0005).
"""

import asyncio
import hashlib
import math
import re
from typing import Any

import httpx

from tejasri.core.errors import ExternalServiceError
from tejasri.domain.interfaces import EMBEDDING_DIM

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    """Deterministic bag-of-hashed-tokens embedding, unit-normalized.

    Not semantically deep, but shared vocabulary between query and note
    produces genuinely closer vectors — enough for recall to be exercised
    honestly in tests and offline demos, with zero dependencies.
    """

    name = "hash"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vec = [0.0] * EMBEDDING_DIM
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[index] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class SentenceTransformerEmbedder:
    """bge-small-en-v1.5 (384-dim) via sentence-transformers, run off-thread."""

    name = "local"

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ExternalServiceError(
                "sentence-transformers not installed; "
                'install with: pip install -e ".[local-embeddings]"'
            ) from exc
        self._model = SentenceTransformer(model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        def _encode() -> list[list[float]]:
            vectors = self._model.encode(texts, normalize_embeddings=True)
            return [list(map(float, v)) for v in vectors]

        return await asyncio.to_thread(_encode)


class GeminiEmbedder:
    """Gemini hosted embeddings, truncated server-side to EMBEDDING_DIM."""

    name = "gemini"
    _URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"

    def __init__(self, api_key: str, model: str = "text-embedding-004") -> None:
        if not api_key:
            raise ExternalServiceError("GEMINI_API_KEY is not configured")
        self._api_key = api_key
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        body = {
            "requests": [
                {
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": t}]},
                    "outputDimensionality": EMBEDDING_DIM,
                }
                for t in texts
            ]
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                self._URL.format(model=self._model),
                params={"key": self._api_key},
                json=body,
            )
        if response.status_code != 200:
            raise ExternalServiceError(f"gemini embeddings failed: {response.status_code}")
        payload: dict[str, Any] = response.json()
        return [e["values"] for e in payload["embeddings"]]
