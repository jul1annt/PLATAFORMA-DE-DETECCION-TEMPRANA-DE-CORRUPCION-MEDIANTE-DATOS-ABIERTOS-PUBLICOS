"""agregar campo formato a fuentes_datos

Revision ID: ca580b3ba398
Revises: 4abb96316f8b
Create Date: 2026-05-10 20:09:24.389604

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca580b3ba398'
down_revision: Union[str, Sequence[str], None] = '4abb96316f8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    tipoformato = sa.Enum('JSON', 'CSV', 'XML', name='tipoformato')
    tipoformato.create(op.get_bind())
    op.add_column('fuentes_datos', sa.Column('formato', tipoformato, nullable=True))


def downgrade() -> None:
    op.drop_column('fuentes_datos', 'formato')
    sa.Enum(name='tipoformato').drop(op.get_bind())
