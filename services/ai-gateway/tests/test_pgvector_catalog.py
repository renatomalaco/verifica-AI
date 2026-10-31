import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ai_gateway.infrastructure.fakes import one_hot
from ai_gateway.infrastructure.pgvector_catalog import PgvectorBrandCatalog

pytestmark = pytest.mark.integration

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
DIM = 768
TEST_BRAND = "Marca de Teste R4"


@pytest.fixture
async def catalog():
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set (needs the migrated Postgres from infra/docker-compose.yml)")
    engine = create_async_engine(DATABASE_URL)
    yield PgvectorBrandCatalog(engine)
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM marcas_protegidas WHERE brand_name = :name"), {"name": TEST_BRAND})
    await engine.dispose()


async def test_nearest_reference_comes_back_with_its_cosine_similarity(catalog):
    await catalog.save_reference(TEST_BRAND, "logo.png", one_hot(7, DIM))

    candidate = await catalog.nearest(one_hot(7, DIM))

    assert candidate is not None
    assert candidate.name == TEST_BRAND
    assert candidate.similarity == pytest.approx(1.0)


async def test_saving_the_same_source_again_replaces_its_embedding(catalog):
    await catalog.save_reference(TEST_BRAND, "login.png", one_hot(8, DIM))
    await catalog.save_reference(TEST_BRAND, "login.png", one_hot(9, DIM))

    candidate = await catalog.nearest(one_hot(9, DIM))

    assert candidate is not None
    assert candidate.name == TEST_BRAND
    assert candidate.similarity == pytest.approx(1.0)
