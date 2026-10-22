"""Preserve anomalies when they leave the active set.

Revision ID: d6e97c4b1a20
Revises: b4d9a0f1c2e3
"""
from alembic import op
import sqlalchemy as sa


revision = "d6e97c4b1a20"
down_revision = "b4d9a0f1c2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contrato_anomalo_incompleto_historial",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("anomalia_id_original", sa.BigInteger(), nullable=False),
        sa.Column("raw_secop_id", sa.BigInteger(), nullable=False),
        sa.Column("id_contrato_procesado", sa.BigInteger(), nullable=True),
        sa.Column("motivo", sa.String(length=50), nullable=True),
        sa.Column("valor_detectado", sa.Text(), nullable=True),
        sa.Column("tipo_anomalia", sa.String(length=50), nullable=True),
        sa.Column("valor_original", sa.Text(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("campo_afectado", sa.String(length=100), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("anomalia_id_original", name="uq_anomalia_historial_original"),
    )
    op.create_index(
        "ix_contrato_anomalia_historial_raw_secop_id",
        "contrato_anomalo_incompleto_historial",
        ["raw_secop_id"],
    )
    op.create_index(
        "ix_contrato_anomalia_historial_id_contrato_procesado",
        "contrato_anomalo_incompleto_historial",
        ["id_contrato_procesado"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contrato_anomalia_historial_id_contrato_procesado",
        table_name="contrato_anomalo_incompleto_historial",
    )
    op.drop_index(
        "ix_contrato_anomalia_historial_raw_secop_id",
        table_name="contrato_anomalo_incompleto_historial",
    )
    op.drop_table("contrato_anomalo_incompleto_historial")
