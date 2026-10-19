"""create marcas_protegidas table and seed data

Revision ID: 0002_marcas_protegidas
Revises: 0001_analises_phishing
Create Date: 2026-10-13

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "0002_marcas_protegidas"
down_revision: Union[str, None] = "0001_analises_phishing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marcas_protegidas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("official_domains", JSON(), nullable=False),
        sa.Column("logo_embedding", JSON(), nullable=False),  # Stores a normalized 512-dim vector
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_marcas_protegidas_brand_name", "marcas_protegidas", ["brand_name"])


def downgrade() -> None:
    op.drop_index("ix_marcas_protegidas_brand_name", table_name="marcas_protegidas")
    op.drop_table("marcas_protegidas")
