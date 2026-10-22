"""Preserve authenticated reviews of historical feature evidence."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = 'c72e3b98f10a'
down_revision = 'bd71c6a4046f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('riesgo_evidencias_variables',
        sa.Column('evidence_id', sa.String(100), primary_key=True),
        sa.Column('record', pg.JSONB(), nullable=False),
        sa.Column('record_sha256', sa.String(64), nullable=False),
        sa.Column('registered_by', sa.Integer(), sa.ForeignKey('admins.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM riesgo_evidencias_variables)')).scalar():
        raise RuntimeError('Conservar las revisiones de evidencia antes de retirar el esquema')
    op.drop_table('riesgo_evidencias_variables')
