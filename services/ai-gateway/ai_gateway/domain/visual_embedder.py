import hashlib
import math
from typing import Protocol


class VisualEmbedderProtocol(Protocol):
    async def embed_image(self, image_b64: str) -> list[float]:
        ...


class FakeVisualEmbedder:
    """Deterministic visual embedder for fast unit tests without a GPU."""

    def __init__(self, default_embedding: list[float] | None = None, dimension: int = 768) -> None:
        self._default = default_embedding
        self._dimension = dimension

    def set_embedding(self, embedding: list[float]) -> None:
        self._default = embedding

    async def embed_image(self, image_b64: str) -> list[float]:
        if self._default is not None:
            return list(self._default)
        return _unit_vector_from_hash(image_b64, self._dimension)


def _unit_vector_from_hash(text: str, dimension: int) -> list[float]:
    raw: list[float] = []
    block = text.encode("ascii")
    while len(raw) < dimension:
        block = hashlib.sha256(block).digest()
        raw.extend(float(b) for b in block)
    raw = raw[:dimension]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw]
