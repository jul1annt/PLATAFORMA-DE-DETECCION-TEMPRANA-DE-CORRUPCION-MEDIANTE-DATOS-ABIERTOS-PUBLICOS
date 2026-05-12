"""crear tabla sincronizacion_historial

Revision ID: 293b580b893f
Revises: 2a5f5d65953c
Create Date: 2026-05-11 23:34:01.831616

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '293b580b893f'
down_revision: Union[str, Sequence[str], None] = '2a5f5d65953c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sincronizacion_historial',
        sa.Column('id',                   sa.Integer(),                        nullable=False),
        sa.Column('fuente_id',            sa.Integer(),                        nullable=False),
        sa.Column('fecha_inicio',         sa.DateTime(timezone=True),          server_default=sa.func.now()),
        sa.Column('fecha_fin',            sa.DateTime(timezone=True),          nullable=True),
        sa.Column('registros_traidos',    sa.BigInteger(),                     default=0),
        sa.Column('registros_insertados', sa.BigInteger(),                     default=0),
        sa.Column('registros_duplicados', sa.BigInteger(),                     default=0),
        sa.Column('estado',               sa.Enum('EN_PROCESO', 'EXITOSO', 'ERROR', name='estadosync')),
        sa.Column('mensaje_error',        sa.Text(),                           nullable=True),
        sa.ForeignKeyConstraint(['fuente_id'], ['fuentes_datos.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_historial_fuente_id',    'sincronizacion_historial', ['fuente_id'])
    op.create_index('ix_historial_fecha_inicio', 'sincronizacion_historial', ['fecha_inicio'])
    op.create_index('ix_historial_estado',       'sincronizacion_historial', ['estado'])

def downgrade() -> None:
    op.drop_index('ix_historial_estado')
    op.drop_index('ix_historial_fecha_inicio')
    op.drop_index('ix_historial_fuente_id')
    op.drop_table('sincronizacion_historial')
    sa.Enum(name='estadosync').drop(op.get_bind())
