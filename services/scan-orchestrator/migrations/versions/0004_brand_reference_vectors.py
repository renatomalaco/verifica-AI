"""store brand reference embeddings as pgvector vectors

Revision ID: 0004_brand_reference_vectors
Revises: 0003_verdict_message_code
Create Date: 2026-10-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "0004_brand_reference_vectors"
down_revision: Union[str, None] = "0003_verdict_message_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# SigLIP base image embeddings; must match ai-gateway's EMBEDDING_DIM.
EMBEDDING_DIM = 768


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Official domains live in contracts.protected_brands; a copy here would drift.
    op.drop_column("marcas_protegidas", "logo_embedding")
    op.drop_column("marcas_protegidas", "official_domains")
    # Several references per brand (logo, official login pages): one row each.
    op.execute(
        f"""
        CREATE TABLE marcas_referencias (
            id UUID PRIMARY KEY,
            brand_id UUID NOT NULL REFERENCES marcas_protegidas (id) ON DELETE CASCADE,
            source VARCHAR(200) NOT NULL,
            logo_embedding vector({EMBEDDING_DIM}) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (brand_id, source)
        )
        """
    )
    # HNSW instead of ivfflat: ivfflat trains its lists when the index is built, and the
    # table is still empty at migration time (the seed runs later), which ruins recall.
    op.execute(
        "CREATE INDEX ix_marcas_referencias_embedding ON marcas_referencias "
        "USING hnsw (logo_embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("marcas_referencias")
    op.add_column("marcas_protegidas", sa.Column("official_domains", JSON(), nullable=False, server_default="[]"))
    op.add_column("marcas_protegidas", sa.Column("logo_embedding", JSON(), nullable=False, server_default="[]"))
