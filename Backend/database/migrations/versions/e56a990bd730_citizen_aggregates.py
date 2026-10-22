"""Persist expensive public aggregates with their immutable data revision."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
revision='e56a990bd730'
down_revision='d42f8b6a901c'
branch_labels=None
depends_on=None


def upgrade():
    op.add_column('riesgo_cortes_ciudadanos',sa.Column('aggregates',pg.JSONB(),nullable=True))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM riesgo_cortes_ciudadanos WHERE aggregates IS NOT NULL)')).scalar():
        raise RuntimeError('Conservar agregados ciudadanos antes de retirar el esquema')
    op.drop_column('riesgo_cortes_ciudadanos','aggregates')
