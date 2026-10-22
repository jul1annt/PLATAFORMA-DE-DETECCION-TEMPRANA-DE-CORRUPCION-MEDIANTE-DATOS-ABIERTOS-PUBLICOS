"""Record analytics executions, including successful empty results.

Revision ID: a16cfe87b3d0
Revises: 8c4b1e9d20af
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a16cfe87b3d0"
down_revision = "8c4b1e9d20af"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analitica_ejecuciones",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("estado", sa.String(length=24), nullable=False),
        sa.Column("parametros", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("universo", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("firma_universo", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_contratos", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("total_resultados", sa.BigInteger(), nullable=True),
        sa.Column("error_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mensaje_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_analitica_ejecuciones_tipo", "analitica_ejecuciones", ["tipo"])
    op.create_index("ix_analitica_ejecuciones_estado", "analitica_ejecuciones", ["estado"])
    op.create_index(
        "ix_analitica_ejecuciones_tipo_inicio",
        "analitica_ejecuciones",
        ["tipo", "fecha_inicio"],
    )


def downgrade() -> None:
    op.drop_index("ix_analitica_ejecuciones_tipo_inicio", table_name="analitica_ejecuciones")
    op.drop_index("ix_analitica_ejecuciones_estado", table_name="analitica_ejecuciones")
    op.drop_index("ix_analitica_ejecuciones_tipo", table_name="analitica_ejecuciones")
    op.drop_table("analitica_ejecuciones")
