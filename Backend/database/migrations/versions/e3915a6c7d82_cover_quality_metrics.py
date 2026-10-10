"""Cover whole-universe quality aggregates without reading wide contract rows."""
from alembic import op

revision = "e3915a6c7d82"
down_revision = "d2804c8b39a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CONCURRENTLY keeps ordinary reads/writes available during this additive DDL.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_cp_metricas_cover", "contratos_procesados",
            ["es_incompleto", "es_sospechoso", "clasificacion_riesgo", "nivel_confianza"],
            unique=False, postgresql_include=["id"], postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index("ix_cp_metricas_cover", table_name="contratos_procesados", postgresql_concurrently=True)
