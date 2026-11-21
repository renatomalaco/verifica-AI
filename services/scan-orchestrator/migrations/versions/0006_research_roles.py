"""research roles with editable permissions

Revision ID: 0006_research_roles
Revises: 0005_research_accounts
Create Date: 2026-11-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0006_research_roles"
down_revision: Union[str, None] = "0005_research_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cargos_pesquisa",
        sa.Column("id", sa.String(length=20), primary_key=True),
        sa.Column("nome", sa.String(length=60), nullable=False, unique=True),
        sa.Column("permissoes", ARRAY(sa.String(length=30)), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    # The two roles accounts already use; admins rename them and add others on the screen.
    # Array literals, because an untyped empty ARRAY[] is an error in Postgres.
    op.execute(
        "INSERT INTO cargos_pesquisa (id, nome, permissoes) VALUES "
        "('admin', 'Administrador', '{run_study,manage_access}'), "
        "('researcher', 'Pesquisador', '{}')"
    )
    op.create_foreign_key(
        "fk_contas_pesquisa_cargo", "contas_pesquisa", "cargos_pesquisa", ["role"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_contas_pesquisa_cargo", "contas_pesquisa", type_="foreignkey")
    op.drop_table("cargos_pesquisa")
