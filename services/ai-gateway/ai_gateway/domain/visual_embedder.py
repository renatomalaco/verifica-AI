import hashlib
import math
from typing import Protocol


class VisualEmbedderProtocol(Protocol):
    async def embed_image(self, image_b64: str) -> list[float]:
        ...


class FakeVisualEmbedder:
    """Deterministic visual embedder for fast unit tests without a GPU."""

    def __init__(self, default_embedding: list[float] | None = None) -> None:
        self._default = default_embedding

    def set_embedding(self, embedding: list[float]) -> None:
        self._default = embedding

    async def embed_image(self, image_b64: str) -> list[float]:
        if self._default is not None:
            return list(self._default)

        # Builds a deterministic unit vector from the image hash
        digest = hashlib.sha256(image_b64.encode("ascii")).digest()
        raw_vals = [float(b) for b in digest[:16]]
        norm = math.sqrt(sum(v * v for v in raw_vals)) or 1.0
        return [round(v / norm, 4) for v in raw_vals]
