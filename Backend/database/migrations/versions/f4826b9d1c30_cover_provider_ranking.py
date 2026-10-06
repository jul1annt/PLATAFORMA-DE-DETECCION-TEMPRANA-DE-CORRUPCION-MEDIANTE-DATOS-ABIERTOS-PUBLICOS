"""Index identified suppliers and their names for bounded dashboard ranking."""
from alembic import op
import sqlalchemy as sa

revision = 'f4826b9d1c30'
down_revision = 'e3915a6c7d82'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.create_index(
            'ix_cp_nit_nombre', 'contratos_procesados',
            ['nit_proveedor_clave', 'proveedor_normalizado'], unique=False,
            postgresql_where=sa.text('nit_proveedor_clave IS NOT NULL'),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index('ix_cp_nit_nombre',table_name='contratos_procesados',postgresql_concurrently=True)
