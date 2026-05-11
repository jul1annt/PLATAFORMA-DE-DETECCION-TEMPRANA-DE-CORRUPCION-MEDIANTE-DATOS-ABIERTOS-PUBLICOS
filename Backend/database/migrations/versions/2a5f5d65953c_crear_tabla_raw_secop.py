"""crear tabla raw_secop

Revision ID: 2a5f5d65953c
Revises: ca580b3ba398
Create Date: 2026-05-10 21:50:35.535493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a5f5d65953c'
down_revision: Union[str, Sequence[str], None] = 'ca580b3ba398'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'raw_secop',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('fuente_id', sa.Integer(), sa.ForeignKey('fuentes_datos.id'), nullable=False),
        sa.Column('entidad', sa.Text()),
        sa.Column('nit_entidad', sa.String(50)),
        sa.Column('departamento_entidad', sa.String(100)),
        sa.Column('ciudad_entidad', sa.String(100)),
        sa.Column('ordenentidad', sa.Text()),
        sa.Column('codigo_pci', sa.String(50)),
        sa.Column('codigo_entidad', sa.Numeric()),
        sa.Column('id_del_proceso', sa.String(100)),
        sa.Column('referencia_del_proceso', sa.Text()),
        sa.Column('ppi', sa.Text()),
        sa.Column('id_del_portafolio', sa.String(100)),
        sa.Column('nombre_del_procedimiento', sa.Text()),
        sa.Column('descripci_n_del_procedimiento', sa.Text()),
        sa.Column('fase', sa.String(100)),
        sa.Column('estado_del_procedimiento', sa.String(100)),
        sa.Column('id_estado_del_procedimiento', sa.Numeric()),
        sa.Column('estado_de_apertura_del_proceso', sa.String(100)),
        sa.Column('estado_resumen', sa.String(100)),
        sa.Column('fecha_de_publicacion_del', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_ultima_publicaci', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_publicacion_fase', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_publicacion_fase_1', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_publicacion', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_publicacion_fase_2', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_publicacion_fase_3', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_recepcion_de', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_apertura_de_respuesta', sa.DateTime(timezone=True)),
        sa.Column('fecha_de_apertura_efectiva', sa.DateTime(timezone=True)),
        sa.Column('fecha_adjudicacion', sa.DateTime(timezone=True)),
        sa.Column('precio_base', sa.Numeric(20, 2)),
        sa.Column('modalidad_de_contratacion', sa.String(200)),
        sa.Column('justificaci_n_modalidad_de', sa.Text()),
        sa.Column('duracion', sa.Numeric()),
        sa.Column('unidad_de_duracion', sa.String(50)),
        sa.Column('tipo_de_contrato', sa.String(200)),
        sa.Column('subtipo_de_contrato', sa.String(200)),
        sa.Column('categorias_adicionales', sa.Text()),
        sa.Column('codigo_principal_de_categoria', sa.String(100)),
        sa.Column('ciudad_de_la_unidad_de', sa.String(100)),
        sa.Column('nombre_de_la_unidad_de', sa.Text()),
        sa.Column('proveedores_invitados', sa.Numeric()),
        sa.Column('proveedores_con_invitacion', sa.Numeric()),
        sa.Column('visualizaciones_del', sa.Numeric()),
        sa.Column('proveedores_que_manifestaron', sa.Numeric()),
        sa.Column('respuestas_al_procedimiento', sa.Numeric()),
        sa.Column('respuestas_externas', sa.Numeric()),
        sa.Column('conteo_de_respuestas_a_ofertas', sa.Numeric()),
        sa.Column('proveedores_unicos_con', sa.Numeric()),
        sa.Column('numero_de_lotes', sa.Numeric()),
        sa.Column('adjudicado', sa.String(10)),
        sa.Column('id_adjudicacion', sa.String(100)),
        sa.Column('codigoproveedor', sa.String(100)),
        sa.Column('departamento_proveedor', sa.String(100)),
        sa.Column('ciudad_proveedor', sa.String(100)),
        sa.Column('valor_total_adjudicacion', sa.Numeric(20, 2)),
        sa.Column('nombre_del_adjudicador', sa.Text()),
        sa.Column('nombre_del_proveedor', sa.Text()),
        sa.Column('nit_del_proveedor_adjudicado', sa.String(50)),
        sa.Column('urlproceso', sa.Text()),
        sa.Column('sincronizado_en', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_raw_secop_id_proceso',   'raw_secop', ['id_del_proceso'], unique=True)
    op.create_index('ix_raw_secop_fecha_pub',     'raw_secop', ['fecha_de_publicacion_del'])
    op.create_index('ix_raw_secop_nit_entidad',   'raw_secop', ['nit_entidad'])
    op.create_index('ix_raw_secop_entidad',       'raw_secop', ['entidad'])
    op.create_index('ix_raw_secop_estado',        'raw_secop', ['estado_del_procedimiento'])
    op.create_index('ix_raw_secop_modalidad',     'raw_secop', ['modalidad_de_contratacion'])
    op.create_index('ix_raw_secop_fuente',        'raw_secop', ['fuente_id'])
    op.create_index('ix_raw_secop_entidad_fecha', 'raw_secop', ['nit_entidad', 'fecha_de_publicacion_del'])
    op.create_index('ix_raw_secop_adjudicado',    'raw_secop', ['adjudicado', 'valor_total_adjudicacion'])


def downgrade() -> None:
    op.drop_index('ix_raw_secop_adjudicado')
    op.drop_index('ix_raw_secop_entidad_fecha')
    op.drop_index('ix_raw_secop_fuente')
    op.drop_index('ix_raw_secop_modalidad')
    op.drop_index('ix_raw_secop_estado')
    op.drop_index('ix_raw_secop_entidad')
    op.drop_index('ix_raw_secop_nit_entidad')
    op.drop_index('ix_raw_secop_fecha_pub')
    op.drop_index('ix_raw_secop_id_proceso')
    op.drop_table('raw_secop')
