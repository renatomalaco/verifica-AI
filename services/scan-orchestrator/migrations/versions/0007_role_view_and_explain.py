"""switches for reading the study and for "Me explica" without quota

Revision ID: 0007_role_view_and_explain
Revises: 0006_research_roles
Create Date: 2026-11-21

"""
from typing import Sequence, Union
from alembic import op

revision: str = "0007_role_view_and_explain"
down_revision: Union[str, None] = "0006_research_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Every role read the report before this switch existed: keep it that way.
    op.execute("UPDATE cargos_pesquisa SET permissoes = array_prepend('view_study', permissoes)")
    op.execute(
        "UPDATE cargos_pesquisa SET permissoes = array_append(permissoes, 'unlimited_explain') "
        "WHERE id = 'admin'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE cargos_pesquisa SET permissoes = "
        "array_remove(array_remove(permissoes, 'view_study'), 'unlimited_explain')"
    )
