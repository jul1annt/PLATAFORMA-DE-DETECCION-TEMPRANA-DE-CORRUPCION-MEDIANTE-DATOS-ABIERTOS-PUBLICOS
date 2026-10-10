"""Keep aggregate coverage while allowing B-tree deduplication of repeated keys."""
from alembic import op
import sqlalchemy as sa

revision = '08c6d9a2e4b1'
down_revision = 'f4826b9d1c30'
branch_labels = None
depends_on = None

NAME = 'ix_cp_metricas_cover'
TEMPORARY = 'ix_cp_metricas_replacement'
COLUMNS = ('es_incompleto', 'es_sospechoso', 'clasificacion_riesgo', 'nivel_confianza')


def _index(name):
    return op.get_bind().execute(sa.text("""
        SELECT i.indisvalid AS valid, i.indisready AS ready, i.indisunique AS unique,
               i.indnkeyatts AS key_count, i.indnatts AS column_count,
               i.indpred IS NULL AND i.indexprs IS NULL AS plain,
               am.amname AS method, tn.nspname AS table_schema, t.relname AS table_name,
               ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY k(attnum,n)
                     JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum
                     ORDER BY k.n) AS columns
        FROM pg_index i JOIN pg_class idx ON idx.oid=i.indexrelid
        JOIN pg_namespace ns ON ns.oid=idx.relnamespace
        JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace tn ON tn.oid=t.relnamespace
        JOIN pg_am am ON am.oid=idx.relam
        WHERE ns.nspname='public' AND idx.relname=:name
    """), {'name': name}).mappings().first()


def _matches(row, include_id):
    columns = COLUMNS + (('id',) if include_id else ())
    return (row is not None and row['valid'] is True and row['ready'] is True
            and row['unique'] is False and row['plain'] is True
            and row['method'] == 'btree' and row['table_schema'] == 'public'
            and row['table_name'] == 'contratos_procesados'
            and row['key_count'] == 4 and row['column_count'] == len(columns)
            and tuple(row['columns']) == columns)


def _replace(include_id):
    # Each committed DDL stage can be resumed without removing an unverified index.
    with op.get_context().autocommit_block():
        current, temporary = _index(NAME), _index(TEMPORARY)
        if _matches(current, include_id):
            if temporary is not None:
                raise RuntimeError('Existe un índice temporal inesperado; conservar y revisar')
            return
        if current is not None and not _matches(current, not include_id):
            raise RuntimeError('El índice anterior no coincide; conservar y revisar')
        if temporary is None:
            options = {'unique': False, 'postgresql_concurrently': True, 'schema': 'public'}
            if include_id:
                options['postgresql_include'] = ['id']
            op.create_index(TEMPORARY, 'contratos_procesados', list(COLUMNS), **options)
            temporary = _index(TEMPORARY)
        if not _matches(temporary, include_id):
            raise RuntimeError('El reemplazo no está válido/listo o difiere; conservar el anterior')
        if current is not None:
            op.drop_index(NAME, table_name='contratos_procesados', schema='public',
                          postgresql_concurrently=True)
        op.execute(f'ALTER INDEX public.{TEMPORARY} RENAME TO {NAME}')


def upgrade():
    _replace(False)


def downgrade():
    _replace(True)
