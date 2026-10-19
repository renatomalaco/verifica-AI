"""store the verdict message code instead of the user-facing text

Revision ID: 0003_verdict_message_code
Revises: 0002_marcas_protegidas
Create Date: 2026-10-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003_verdict_message_code"
down_revision: Union[str, None] = "0002_marcas_protegidas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The wording moved to the front end's dictionary; only the code is a fact worth keeping.
    op.add_column(
        "analises_phishing",
        sa.Column("verdict_message", sa.String(length=40), nullable=False, server_default="inconclusive"),
    )
    op.drop_column("analises_phishing", "verdict_plain")
    op.drop_column("analises_phishing", "action_advice")


def downgrade() -> None:
    op.add_column("analises_phishing", sa.Column("action_advice", sa.Text(), nullable=False, server_default=""))
    op.add_column("analises_phishing", sa.Column("verdict_plain", sa.Text(), nullable=False, server_default=""))
    op.drop_column("analises_phishing", "verdict_message")
