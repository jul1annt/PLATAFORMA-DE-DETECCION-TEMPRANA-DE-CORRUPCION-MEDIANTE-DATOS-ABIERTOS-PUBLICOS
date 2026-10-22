"""Archive duplicate active anomalies and prevent them recurring.

Revision ID: f42b38e1a760
Revises: e13ad9c24780
"""
from alembic import op
import sqlalchemy as sa


revision = "f42b38e1a760"
down_revision = "e13ad9c24780"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO contrato_anomalo_incompleto_historial (
            anomalia_id_original,
            raw_secop_id,
            id_contrato_procesado,
            motivo,
            valor_detectado,
            tipo_anomalia,
            valor_original,
            descripcion,
            campo_afectado,
            fecha_inicio,
            fecha_fin
        )
        SELECT
            anomaly.id,
            anomaly.raw_secop_id,
            anomaly.id_contrato_procesado,
            anomaly.motivo,
            anomaly.valor_detectado,
            anomaly.tipo_anomalia,
            anomaly.valor_original,
            anomaly.descripcion,
            anomaly.campo_afectado,
            anomaly.created_at,
            now()
        FROM (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY raw_secop_id,
                                    COALESCE(tipo_anomalia, motivo, 'SIN_TIPO'),
                                    campo_afectado
                       ORDER BY created_at DESC, id DESC
                   ) AS duplicate_number
            FROM contrato_anomalo_incompleto
        ) duplicates
        JOIN contrato_anomalo_incompleto anomaly ON anomaly.id = duplicates.id
        WHERE duplicates.duplicate_number > 1
    """)
    op.execute("""
        WITH duplicates AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY raw_secop_id,
                                    COALESCE(tipo_anomalia, motivo, 'SIN_TIPO'),
                                    campo_afectado
                       ORDER BY created_at DESC, id DESC
                   ) AS duplicate_number
            FROM contrato_anomalo_incompleto
        )
        DELETE FROM contrato_anomalo_incompleto anomaly
        USING duplicates
        WHERE anomaly.id = duplicates.id
          AND duplicates.duplicate_number > 1
    """)
    op.create_index(
        "uq_cai_raw_tipo_campo",
        "contrato_anomalo_incompleto",
        [
            "raw_secop_id",
            sa.text("COALESCE(tipo_anomalia, motivo, 'SIN_TIPO')"),
            "campo_afectado",
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_cai_raw_tipo_campo", table_name="contrato_anomalo_incompleto")
