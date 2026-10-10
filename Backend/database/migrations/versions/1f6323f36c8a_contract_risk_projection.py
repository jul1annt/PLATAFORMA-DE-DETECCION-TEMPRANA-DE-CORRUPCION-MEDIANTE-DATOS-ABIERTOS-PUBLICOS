"""Project current provider risk onto processed contracts.

Revision ID: 1f6323f36c8a
Revises: 66a829f96a31
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "1f6323f36c8a"
down_revision = "66a829f96a31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contratos_procesados", sa.Column(
        "clasificacion_riesgo", sa.String(length=20), server_default="SIN_EVALUAR", nullable=False
    ))
    op.add_column("contratos_procesados", sa.Column("score_riesgo", sa.Numeric(20, 4), nullable=True))
    op.add_column("contratos_procesados", sa.Column("riesgo_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_contratos_procesados_clasificacion_riesgo", "contratos_procesados", ["clasificacion_riesgo"])
    op.create_index("ix_contratos_procesados_riesgo_run_id", "contratos_procesados", ["riesgo_run_id"])


def downgrade() -> None:
    op.drop_index("ix_contratos_procesados_riesgo_run_id", table_name="contratos_procesados")
    op.drop_index("ix_contratos_procesados_clasificacion_riesgo", table_name="contratos_procesados")
    op.drop_column("contratos_procesados", "riesgo_run_id")
    op.drop_column("contratos_procesados", "score_riesgo")
    op.drop_column("contratos_procesados", "clasificacion_riesgo")
