"""Make raw record identity authoritative for processed contracts.

Revision ID: 66a829f96a31
Revises: 4d2f8b8f8b10
"""
from alembic import op

revision = "66a829f96a31"
down_revision = "4d2f8b8f8b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Conserva el registro procesado más reciente por origen y reasigna sus anomalías.
    # Esto hace que la restricción pueda instalarse incluso sobre datos históricos.
    op.execute("""
        WITH duplicate_map AS (
            SELECT id AS old_id, MAX(id) OVER (PARTITION BY raw_secop_id) AS keep_id
            FROM contratos_procesados
        )
        UPDATE contrato_anomalo_incompleto AS anomaly
        SET id_contrato_procesado = duplicate_map.keep_id
        FROM duplicate_map
        WHERE anomaly.id_contrato_procesado = duplicate_map.old_id
          AND duplicate_map.old_id <> duplicate_map.keep_id
    """)
    op.execute("""
        DELETE FROM contratos_procesados AS contract
        USING (
            SELECT id, MAX(id) OVER (PARTITION BY raw_secop_id) AS keep_id
            FROM contratos_procesados
        ) AS duplicate_map
        WHERE contract.id = duplicate_map.id
          AND duplicate_map.id <> duplicate_map.keep_id
    """)
    op.drop_index("ix_contratos_procesados_normalized_hash", table_name="contratos_procesados")
    op.create_index(
        "ix_contratos_procesados_normalized_hash",
        "contratos_procesados",
        ["normalized_hash"],
        unique=False,
    )
    op.drop_index("ix_contratos_procesados_raw_secop_id", table_name="contratos_procesados")
    op.create_index(
        "ix_contratos_procesados_raw_secop_id",
        "contratos_procesados",
        ["raw_secop_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_contratos_procesados_raw_secop_id", table_name="contratos_procesados")
    op.create_index(
        "ix_contratos_procesados_raw_secop_id",
        "contratos_procesados",
        ["raw_secop_id"],
        unique=False,
    )
    op.drop_index("ix_contratos_procesados_normalized_hash", table_name="contratos_procesados")
    op.create_index(
        "ix_contratos_procesados_normalized_hash",
        "contratos_procesados",
        ["normalized_hash"],
        unique=True,
    )
