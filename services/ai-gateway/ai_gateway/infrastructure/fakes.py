import hashlib
import math

from ai_gateway.domain.brand_matcher import BrandCandidate


class FakeVisualEmbedder:
    """Deterministic visual embedder for fast unit tests without the SigLIP model."""

    def __init__(self, default_embedding: list[float] | None = None, dimension: int = 768) -> None:
        self._default = default_embedding
        self._dimension = dimension

    async def embed_image(self, image_b64: str) -> list[float]:
        if self._default is not None:
            return list(self._default)
        return _unit_vector_from_hash(image_b64, self._dimension)


class FakeBrandCatalog:
    """In-memory nearest neighbour by cosine similarity, standing in for pgvector."""

    def __init__(self, references: dict[str, list[list[float]]]) -> None:
        self._references = references

    async def nearest(self, embedding: list[float]) -> BrandCandidate | None:
        candidates = [
            BrandCandidate(name=brand, similarity=cosine_similarity(embedding, vector))
            for brand, vectors in self._references.items()
            for vector in vectors
        ]
        return max(candidates, key=lambda c: c.similarity, default=None)


class FakeBrandVerifier:
    def __init__(self, answer: bool = False, error: Exception | None = None) -> None:
        self._answer = answer
        self._error = error
        self.calls = 0

    async def shows_brand(self, image_b64: str, brand: str) -> bool:
        self.calls += 1
        if self._error:
            raise self._error
        return self._answer


def one_hot(index: int, dimension: int) -> list[float]:
    return [1.0 if i == index else 0.0 for i in range(dimension)]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Embedding dimension {len(vec_a)} does not match the catalog dimension {len(vec_b)}")
    norm = math.sqrt(sum(a * a for a in vec_a)) * math.sqrt(sum(b * b for b in vec_b))
    if norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(vec_a, vec_b)) / norm


def _unit_vector_from_hash(text: str, dimension: int) -> list[float]:
    raw: list[float] = []
    block = text.encode("ascii")
    while len(raw) < dimension:
        block = hashlib.sha256(block).digest()
        raw.extend(float(b) for b in block)
    raw = raw[:dimension]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw]
