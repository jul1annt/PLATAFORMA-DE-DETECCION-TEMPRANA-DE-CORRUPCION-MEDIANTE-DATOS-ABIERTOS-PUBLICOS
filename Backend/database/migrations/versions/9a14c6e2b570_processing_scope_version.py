"""Record transformation rule version and run universe.

Revision ID: 9a14c6e2b570
Revises: f42b38e1a760
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9a14c6e2b570"
down_revision = "f42b38e1a760"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "procesamiento_logs",
        sa.Column("version_reglas", sa.String(length=32), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "procesamiento_logs",
        sa.Column(
            "universo",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("procesamiento_logs", "version_reglas", server_default=None)
    op.alter_column("procesamiento_logs", "universo", server_default=None)


def downgrade() -> None:
    op.drop_column("procesamiento_logs", "universo")
    op.drop_column("procesamiento_logs", "version_reglas")
