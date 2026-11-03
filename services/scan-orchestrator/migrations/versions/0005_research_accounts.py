"""research area accounts and rotating refresh sessions (R5a)

Revision ID: 0005_research_accounts
Revises: 0004_brand_reference_vectors
Create Date: 2026-10-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005_research_accounts"
down_revision: Union[str, None] = "0004_brand_reference_vectors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only researchers have accounts; people checking messages stay anonymous.
    op.create_table(
        "contas_pesquisa",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False, unique=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invite_hash", sa.String(length=64), nullable=True, unique=True),
        sa.Column("invite_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_table(
        "sessoes_pesquisa",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contas_pesquisa.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_sessoes_pesquisa_account_id", "sessoes_pesquisa", ["account_id"])
    op.create_index("ix_sessoes_pesquisa_family_id", "sessoes_pesquisa", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_sessoes_pesquisa_family_id", table_name="sessoes_pesquisa")
    op.drop_index("ix_sessoes_pesquisa_account_id", table_name="sessoes_pesquisa")
    op.drop_table("sessoes_pesquisa")
    op.drop_table("contas_pesquisa")
