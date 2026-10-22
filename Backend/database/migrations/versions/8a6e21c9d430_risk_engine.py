"""Isolated, versioned analytical models and atomic publication pointer."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = '8a6e21c9d430'
down_revision = '3c19a8f7e2d0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('riesgo_casos', sa.Column('case_id', sa.String(100), primary_key=True),
        sa.Column('record', pg.JSONB(), nullable=False), sa.Column('record_sha256', sa.String(64), nullable=False),
        sa.Column('eligible', sa.Boolean(), nullable=False), sa.Column('exclusions', pg.JSONB(), nullable=False),
        sa.Column('registered_by', sa.Integer(), sa.ForeignKey('admins.id'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('riesgo_modelos', sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('stage', sa.String(20), nullable=False), sa.Column('version', sa.String(100), unique=True, nullable=False),
        sa.Column('artifact', pg.JSONB(), nullable=False), sa.Column('report', pg.JSONB(), nullable=False),
        sa.Column('validated', sa.Boolean(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('riesgo_cortes', sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('status', sa.String(30), nullable=False), sa.Column('context', pg.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column('finished_at', sa.DateTime(timezone=True)))
    op.create_table('riesgo_resultados', sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('cut_id', pg.UUID(as_uuid=True), sa.ForeignKey('riesgo_cortes.id'), nullable=False),
        sa.Column('raw_secop_id', sa.BigInteger(), sa.ForeignKey('raw_secop.id'), nullable=False),
        sa.Column('stage', sa.String(20), nullable=False), sa.Column('result', pg.JSONB(), nullable=False))
    op.create_index('uq_riesgo_resultado_operacion', 'riesgo_resultados', ['cut_id', 'raw_secop_id', 'stage'], unique=True)
    op.create_table('riesgo_publicacion', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cut_id', pg.UUID(as_uuid=True), sa.ForeignKey('riesgo_cortes.id')),
        sa.Column('model_ids', pg.JSONB(), nullable=False), sa.Column('daily_enabled', sa.Boolean(), nullable=False),
        sa.Column('last_attempt_day', sa.String(10)), sa.Column('last_success_day', sa.String(10)),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('id=1', name='ck_riesgo_publicacion_singleton'))
    op.create_table('riesgo_auditoria', sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('action', sa.String(60), nullable=False), sa.Column('actor', sa.String(100), nullable=False),
        sa.Column('detail', pg.JSONB(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.execute("INSERT INTO riesgo_publicacion(id,model_ids,daily_enabled) VALUES (1,'{}'::jsonb,false)")


def downgrade():
    # Refuse to discard case/model/publication evidence through a routine downgrade.
    for table in ('riesgo_resultados', 'riesgo_modelos', 'riesgo_casos', 'riesgo_auditoria', 'riesgo_cortes'):
        if op.get_bind().execute(sa.text(f'SELECT EXISTS(SELECT 1 FROM {table})')).scalar():
            raise RuntimeError('Conservar evidencias analíticas: exportar y revisar antes de retirar el esquema')
    for table in ('riesgo_publicacion', 'riesgo_resultados', 'riesgo_cortes', 'riesgo_modelos', 'riesgo_casos', 'riesgo_auditoria'):
        op.drop_table(table)
