"""create analises_phishing table

Revision ID: 0001_analises_phishing
Revises: 
Create Date: 2026-10-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision: str = "0001_analises_phishing"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable the pgvector extension if available in Postgres
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Create the audit, history and telemetry table
    op.create_table(
        "analises_phishing",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_type", sa.String(length=20), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("threat_level", sa.String(length=30), nullable=False),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("verdict_plain", sa.Text(), nullable=False),
        sa.Column("action_advice", sa.Text(), nullable=False),
        sa.Column("latency_breakdown", JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_analises_phishing_input_hash", "analises_phishing", ["input_hash"])


def downgrade() -> None:
    op.drop_index("ix_analises_phishing_input_hash", table_name="analises_phishing")
    op.drop_table("analises_phishing")
