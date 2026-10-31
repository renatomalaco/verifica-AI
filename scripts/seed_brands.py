"""
Seeds the Visual RAG catalog (marcas_referencias) with SigLIP embeddings of reference images.

Images go in data/brands/<brand-folder>/ (git-ignored: logos are trademarks). Use the official
logo and screenshots of each brand's real login pages, and record where and when each image
was obtained in data/brands/<brand-folder>/FONTES.md. Only the embeddings reach the database.

    uv sync --all-packages --extra siglip
    $env:DATABASE_URL = "postgresql+asyncpg://..."   # the migrated Postgres
    uv run python scripts/seed_brands.py [data/brands]

Running it again replaces the embedding of each image already seeded (same folder/file).
"""
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from ai_gateway.application.seed_brands import brand_folders, seed_references
from ai_gateway.infrastructure.pgvector_catalog import PgvectorBrandCatalog
from ai_gateway.infrastructure.siglip_embedder import SiglipEmbedder
from ai_gateway.settings import Settings


async def main(root: Path) -> int:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("Set DATABASE_URL to the migrated Postgres.", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"{root} not found. Expected one folder per brand: {sorted(brand_folders())}", file=sys.stderr)
        return 2

    settings = Settings()
    engine = create_async_engine(database_url)
    try:
        embedder = SiglipEmbedder(model_name=settings.SIGLIP_MODEL, dimension=settings.EMBEDDING_DIM)
        saved = await seed_references(root, embedder, PgvectorBrandCatalog(engine))
    finally:
        await engine.dispose()
    print(f"{saved} reference images embedded and stored.")
    return 0 if saved else 1


if __name__ == "__main__":
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/brands")
    sys.exit(asyncio.run(main(folder)))
