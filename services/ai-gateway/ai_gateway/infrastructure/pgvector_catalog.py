from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ai_gateway.domain.brand_matcher import BrandCandidate

# The vector goes as text and is cast in SQL, so asyncpg needs no pgvector codec.
_NEAREST = text(
    """
    SELECT m.brand_name, 1 - (r.logo_embedding <=> CAST(CAST(:query AS TEXT) AS vector)) AS similarity
    FROM marcas_referencias r
    JOIN marcas_protegidas m ON m.id = r.brand_id
    ORDER BY r.logo_embedding <=> CAST(CAST(:query AS TEXT) AS vector)
    LIMIT 1
    """
)

_UPSERT_BRAND = text(
    """
    INSERT INTO marcas_protegidas (id, brand_name) VALUES (:id, :name)
    ON CONFLICT (brand_name) DO UPDATE SET brand_name = EXCLUDED.brand_name
    RETURNING id
    """
)

_UPSERT_REFERENCE = text(
    """
    INSERT INTO marcas_referencias (id, brand_id, source, logo_embedding)
    VALUES (:id, :brand_id, :source, CAST(CAST(:embedding AS TEXT) AS vector))
    ON CONFLICT (brand_id, source) DO UPDATE SET logo_embedding = EXCLUDED.logo_embedding
    """
)


class PgvectorBrandCatalog:
    """Protected brand references in Postgres, searched by cosine distance (<=>) on an HNSW index."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def nearest(self, embedding: list[float]) -> BrandCandidate | None:
        async with self._engine.connect() as conn:
            row = (await conn.execute(_NEAREST, {"query": _vector_literal(embedding)})).first()
        if row is None:
            return None
        return BrandCandidate(name=row.brand_name, similarity=float(row.similarity))

    async def save_reference(self, brand: str, source: str, embedding: list[float]) -> None:
        async with self._engine.begin() as conn:
            brand_id = (await conn.execute(_UPSERT_BRAND, {"id": uuid4(), "name": brand})).scalar_one()
            await conn.execute(
                _UPSERT_REFERENCE,
                {"id": uuid4(), "brand_id": brand_id, "source": source, "embedding": _vector_literal(embedding)},
            )


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(float(v)) for v in embedding) + "]"
