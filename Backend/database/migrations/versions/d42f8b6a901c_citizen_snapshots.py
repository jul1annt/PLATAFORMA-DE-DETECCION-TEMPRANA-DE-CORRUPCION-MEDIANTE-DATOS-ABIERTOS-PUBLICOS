"""Incremental before images for coherent, reversible public snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = 'd42f8b6a901c'
down_revision = 'c72e3b98f10a'
branch_labels = None
depends_on = None
TABLES = ('contratos_procesados', 'contrato_anomalo_incompleto',
          'contratos_metricas_calidad', 'estadistica_campos_faltantes')


def upgrade():
    op.create_table('riesgo_cortes_ciudadanos',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True),
        sa.Column('revision', sa.BigInteger(), nullable=False),
        sa.Column('risk_cut_id', pg.UUID(as_uuid=True), sa.ForeignKey('riesgo_cortes.id')),
        sa.Column('data_cut_at', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table('riesgo_publicacion_ciudadana',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_id', pg.UUID(as_uuid=True), sa.ForeignKey('riesgo_cortes_ciudadanos.id'), nullable=False),
        sa.CheckConstraint('id=1', name='ck_riesgo_publicacion_ciudadana_singleton'))
    op.execute('CREATE SCHEMA riesgo_historial')
    op.execute('CREATE SCHEMA riesgo_ciudadano')
    op.execute('CREATE SEQUENCE public.riesgo_revision_ciudadana AS bigint')
    # PG15 adds the constant metadata default without copying the source heap.
    # Only changed rows acquire before images, never a full daily clone.
    for table in TABLES:
        op.execute(f'ALTER TABLE public.{table} ADD COLUMN riesgo_desde_revision bigint NOT NULL DEFAULT 0')
        op.execute(f'CREATE TABLE riesgo_historial.{table} (LIKE public.{table}, riesgo_hasta_revision bigint NOT NULL)')
        op.execute(f'CREATE UNIQUE INDEX ON riesgo_historial.{table}(id,riesgo_desde_revision)')
        op.execute(f'CREATE INDEX ON riesgo_historial.{table}(riesgo_hasta_revision)')
    # Public predicates can use their usual indexes in both UNION branches.
    for columns in ('raw_secop_id', 'fecha_publicacion_normalizada,id', 'nit_proveedor_clave,proveedor_normalizado',
                    'valor_total_normalizado', 'entidad_normalizada', 'proveedor_normalizado', 'id_del_proceso'):
        op.execute(f'CREATE INDEX ON riesgo_historial.contratos_procesados({columns})')
    op.execute('CREATE INDEX ON riesgo_historial.contrato_anomalo_incompleto(raw_secop_id)')
    op.execute('''CREATE FUNCTION public.riesgo_version_ciudadana() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
        DECLARE rev bigint;
        BEGIN
            IF TG_LEVEL='STATEMENT' THEN
                IF TG_OP='TRUNCATE' THEN
                    RAISE EXCEPTION 'Conservar versiones ciudadanas: TRUNCATE no está permitido';
                END IF;
                PERFORM set_config('riesgo.write_revision',nextval('public.riesgo_revision_ciudadana')::text,true);
                RETURN NULL;
            END IF;
            rev:=current_setting('riesgo.write_revision')::bigint;
            IF TG_OP IN ('UPDATE','DELETE') THEN
                EXECUTE format('INSERT INTO riesgo_historial.%I SELECT ($1).*, $2',TG_TABLE_NAME) USING OLD,rev;
            END IF;
            IF TG_OP='DELETE' THEN RETURN OLD; END IF;
            NEW.riesgo_desde_revision:=rev;
            RETURN NEW;
        END $$''')
    for table in TABLES:
        op.execute(f'''CREATE TRIGGER risk_public_statement BEFORE INSERT OR UPDATE OR DELETE OR TRUNCATE
            ON public.{table} FOR EACH STATEMENT EXECUTE FUNCTION public.riesgo_version_ciudadana()''')
        op.execute(f'''CREATE TRIGGER risk_public_row BEFORE INSERT OR UPDATE OR DELETE
            ON public.{table} FOR EACH ROW EXECUTE FUNCTION public.riesgo_version_ciudadana()''')
        columns = op.get_bind().execute(sa.text('''SELECT attname FROM pg_attribute
            WHERE attrelid=to_regclass(:table) AND attnum>0 AND NOT attisdropped
            ORDER BY attnum'''), {'table':'public.'+table}).scalars().all()
        names = ','.join('"'+name+'"' for name in columns)
        # A request must explicitly pin a revision. Missing settings fail closed.
        rev = "current_setting('riesgo.public_revision')::bigint"
        op.execute(f'''CREATE VIEW riesgo_ciudadano.{table} AS
            SELECT {names} FROM public.{table} WHERE riesgo_desde_revision<={rev}
            UNION ALL SELECT {names} FROM riesgo_historial.{table}
            WHERE riesgo_desde_revision<={rev} AND riesgo_hasta_revision>{rev}''')


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS(SELECT 1 FROM riesgo_cortes_ciudadanos)')).scalar():
        raise RuntimeError('Conservar cortes ciudadanos antes de retirar el esquema')
    for table in TABLES:
        if op.get_bind().execute(sa.text(f'SELECT EXISTS(SELECT 1 FROM riesgo_historial.{table})')).scalar():
            raise RuntimeError('Conservar historial ciudadano antes de retirar el esquema')
    for table in reversed(TABLES):
        op.execute(f'DROP VIEW riesgo_ciudadano.{table}')
        op.execute(f'DROP TRIGGER risk_public_row ON public.{table}')
        op.execute(f'DROP TRIGGER risk_public_statement ON public.{table}')
        op.execute(f'DROP TABLE riesgo_historial.{table}')
        op.execute(f'ALTER TABLE public.{table} DROP COLUMN riesgo_desde_revision')
    op.execute('DROP FUNCTION public.riesgo_version_ciudadana()')
    op.execute('DROP SEQUENCE public.riesgo_revision_ciudadana')
    op.execute('DROP SCHEMA riesgo_ciudadano')
    op.execute('DROP SCHEMA riesgo_historial')
    op.drop_table('riesgo_publicacion_ciudadana')
    op.drop_table('riesgo_cortes_ciudadanos')
