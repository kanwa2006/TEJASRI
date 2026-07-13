"""HashingEmbedder: deterministic, correctly dimensioned, similarity-bearing."""

import math

from tejasri.domain.interfaces import EMBEDDING_DIM
from tejasri.infrastructure.embeddings import HashingEmbedder


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _l2(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


async def test_embeddings_are_deterministic_and_unit_norm() -> None:
    embedder = HashingEmbedder()
    first, second = await embedder.embed(["metformin 500mg twice daily"] * 2)
    assert first == second
    assert len(first) == EMBEDDING_DIM
    assert abs(_norm(first) - 1.0) < 1e-9


async def test_shared_vocabulary_means_closer_vectors() -> None:
    embedder = HashingEmbedder()
    query, related, unrelated = await embedder.embed(
        [
            "diabetes medication metformin",
            "patient started metformin for type 2 diabetes",
            "sprained ankle treated with rest and ice",
        ]
    )
    assert _l2(query, related) < _l2(query, unrelated)


async def test_empty_text_produces_a_valid_vector() -> None:
    embedder = HashingEmbedder()
    (vector,) = await embedder.embed([""])
    assert len(vector) == EMBEDDING_DIM  # zero vector, but correctly shaped
