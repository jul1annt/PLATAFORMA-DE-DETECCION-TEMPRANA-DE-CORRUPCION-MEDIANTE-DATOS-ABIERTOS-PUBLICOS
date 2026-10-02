"""Clear provider risk projections from processed contract records.

Revision ID: 8c4b1e9d20af
Revises: 7b2acfd82e41
"""
from alembic import op


revision = "8c4b1e9d20af"
down_revision = "7b2acfd82e41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Provider scores are not contract scores. Until a contract-specific,
    # versioned rule exists, prior projections must not be shown as contract risk.
    op.execute("""
        UPDATE contratos_procesados
        SET clasificacion_riesgo = 'SIN_EVALUAR',
            score_riesgo = NULL,
            riesgo_run_id = NULL
        WHERE clasificacion_riesgo IS DISTINCT FROM 'SIN_EVALUAR'
           OR score_riesgo IS NOT NULL
           OR riesgo_run_id IS NOT NULL
    """)


def downgrade() -> None:
    # The previous contract values were projections without independent
    # provenance, so they cannot be reconstructed safely.
    pass
