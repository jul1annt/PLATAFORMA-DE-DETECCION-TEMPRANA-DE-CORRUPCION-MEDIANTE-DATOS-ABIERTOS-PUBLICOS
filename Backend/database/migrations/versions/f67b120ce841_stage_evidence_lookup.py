"""Index explicitly reviewed source-row/stage identities without inferring IDs."""
from alembic import op
import sqlalchemy as sa

revision = 'f67b120ce841'
down_revision = 'e56a990bd730'
branch_labels = None
depends_on = None


def upgrade():
    # Prior reviews remain preserved but are not silently assigned identities.
    # Register a new explicit review before using one in batch inference.
    op.add_column('riesgo_evidencias_variables',sa.Column('raw_secop_id',sa.BigInteger(),sa.ForeignKey('raw_secop.id'),nullable=True))
    op.add_column('riesgo_evidencias_variables',sa.Column('stage',sa.String(20),nullable=True))
    op.add_column('riesgo_evidencias_variables',sa.Column('prediction_at',sa.DateTime(timezone=True),nullable=True))
    op.create_check_constraint('ck_riesgo_evidencia_etapa','riesgo_evidencias_variables',
        "(raw_secop_id IS NULL AND stage IS NULL AND prediction_at IS NULL) OR "
        "(raw_secop_id IS NOT NULL AND raw_secop_id>0 AND stage IS NOT NULL AND stage IN ('CONVOCATORIA','ADJUDICACION') AND prediction_at IS NOT NULL)")
    op.create_index('ix_riesgo_evidencia_operacion_etapa','riesgo_evidencias_variables',['raw_secop_id','stage','created_at'])


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM riesgo_evidencias_variables WHERE raw_secop_id IS NOT NULL)')).scalar():
        raise RuntimeError('Conservar las identidades de evidencia revisadas antes de retirar el esquema')
    op.drop_index('ix_riesgo_evidencia_operacion_etapa',table_name='riesgo_evidencias_variables')
    op.drop_constraint('ck_riesgo_evidencia_etapa','riesgo_evidencias_variables',type_='check')
    for column in ('prediction_at','stage','raw_secop_id'):
        op.drop_column('riesgo_evidencias_variables',column)
