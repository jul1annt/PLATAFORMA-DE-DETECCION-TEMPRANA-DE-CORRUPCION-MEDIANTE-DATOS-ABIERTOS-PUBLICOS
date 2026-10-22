"""Add an explicit partial state for capped source synchronizations.

Revision ID: b4d9a0f1c2e3
Revises: a16cfe87b3d0
"""

from alembic import op


revision = "b4d9a0f1c2e3"
down_revision = "a16cfe87b3d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE estadosync ADD VALUE IF NOT EXISTS 'PARCIAL'")


def downgrade() -> None:
    op.execute(
        "UPDATE sincronizacion_historial SET estado = 'ERROR' WHERE estado = 'PARCIAL'"
    )
    op.execute("ALTER TABLE sincronizacion_historial ALTER COLUMN estado DROP DEFAULT")
    op.execute("ALTER TYPE estadosync RENAME TO estadosync_with_partial")
    op.execute("CREATE TYPE estadosync AS ENUM ('EN_PROCESO', 'EXITOSO', 'ERROR')")
    op.execute(
        "ALTER TABLE sincronizacion_historial ALTER COLUMN estado "
        "TYPE estadosync USING estado::text::estadosync"
    )
    op.execute("DROP TYPE estadosync_with_partial")
