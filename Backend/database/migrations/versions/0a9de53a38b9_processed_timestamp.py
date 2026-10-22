"""Track when a raw record was last transformed.

Revision ID: 0a9de53a38b9
Revises: 1f6323f36c8a
"""
from alembic import op
import sqlalchemy as sa

revision = "0a9de53a38b9"
down_revision = "1f6323f36c8a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contratos_procesados",
        sa.Column("procesado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("UPDATE contratos_procesados SET procesado_en = created_at")


def downgrade() -> None:
    op.drop_column("contratos_procesados", "procesado_en")
