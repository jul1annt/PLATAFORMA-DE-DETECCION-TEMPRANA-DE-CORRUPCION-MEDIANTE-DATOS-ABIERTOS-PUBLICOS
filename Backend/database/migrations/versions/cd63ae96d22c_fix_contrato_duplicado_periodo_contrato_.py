"""Fix contrato_duplicado_periodo contrato_id bigint

Revision ID: cd63ae96d22c
Revises: 2770116ccdda
Create Date: 2026-05-13 18:06:01.846647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cd63ae96d22c'
down_revision: Union[str, Sequence[str], None] = '2770116ccdda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop and recreate table with BigInteger for contrato_id columns."""
    op.drop_index('ix_contrato_duplicado_contrato_id', table_name='contrato_duplicado_periodo', if_exists=True)
    op.drop_index('ix_contrato_duplicado_riesgo', table_name='contrato_duplicado_periodo', if_exists=True)
    op.drop_index('ix_contrato_duplicado_run_id', table_name='contrato_duplicado_periodo', if_exists=True)
    op.drop_index('ix_contrato_duplicado_score', table_name='contrato_duplicado_periodo', if_exists=True)
    op.drop_table('contrato_duplicado_periodo')

    op.create_table(
        'contrato_duplicado_periodo',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contrato_id', sa.BigInteger(), nullable=False),
        sa.Column('contrato_relacionado_id', sa.BigInteger(), nullable=False),
        sa.Column('proveedor', sa.String(255), nullable=False),
        sa.Column('entidad', sa.String(255), nullable=False),
        sa.Column('tipo_contrato', sa.String(255), nullable=True),
        sa.Column('modalidad_contratacion', sa.String(255), nullable=True),
        sa.Column('fecha_contrato', sa.Date(), nullable=False),
        sa.Column('fecha_relacionada', sa.Date(), nullable=False),
        sa.Column('diferencia_dias', sa.Integer(), nullable=False),
        sa.Column('duplicado_score', sa.Numeric(10, 2), nullable=False),
        sa.Column('clasificacion_riesgo', sa.String(50), nullable=False),
        sa.Column('fecha_calculo', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_contrato_duplicado_run_id', 'contrato_duplicado_periodo', ['run_id'])
    op.create_index('ix_contrato_duplicado_contrato_id', 'contrato_duplicado_periodo', ['contrato_id'])
    op.create_index('ix_contrato_duplicado_score', 'contrato_duplicado_periodo', ['duplicado_score'])
    op.create_index('ix_contrato_duplicado_riesgo', 'contrato_duplicado_periodo', ['clasificacion_riesgo'])


def downgrade() -> None:
    """Drop table (no rollback data)."""
    op.drop_index('ix_contrato_duplicado_contrato_id', table_name='contrato_duplicado_periodo')
    op.drop_index('ix_contrato_duplicado_riesgo', table_name='contrato_duplicado_periodo')
    op.drop_index('ix_contrato_duplicado_run_id', table_name='contrato_duplicado_periodo')
    op.drop_index('ix_contrato_duplicado_score', table_name='contrato_duplicado_periodo')
    op.drop_table('contrato_duplicado_periodo')
