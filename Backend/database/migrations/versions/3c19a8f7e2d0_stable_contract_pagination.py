"""Cover date and ID ordering without sorting all contracts tied on one date."""
from alembic import op
import sqlalchemy as sa

revision = '3c19a8f7e2d0'
down_revision = '2ab7c4e8d910'
branch_labels = None
depends_on = None
NAME = 'ix_cp_fecha_publicacion_id'
COLUMNS = ('fecha_publicacion_normalizada', 'id')


def _index():
    return op.get_bind().execute(sa.text("""
        SELECT i.indisvalid AS valid,i.indisready AS ready,i.indisunique AS unique,
               i.indnkeyatts AS key_count,i.indnatts AS column_count,
               i.indpred IS NULL AND i.indexprs IS NULL AS plain,
               am.amname AS method,tn.nspname AS table_schema,t.relname AS table_name,
               ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY k(attnum,n)
                     JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=k.attnum ORDER BY k.n) AS columns,
               ARRAY(SELECT o FROM unnest(i.indoption) o) AS option_flags
        FROM pg_index i JOIN pg_class idx ON idx.oid=i.indexrelid
        JOIN pg_namespace ns ON ns.oid=idx.relnamespace
        JOIN pg_class t ON t.oid=i.indrelid JOIN pg_namespace tn ON tn.oid=t.relnamespace
        JOIN pg_am am ON am.oid=idx.relam
        WHERE ns.nspname='public' AND idx.relname=:name
    """), {'name': NAME}).mappings().first()


def _matches(row):
    return (row is not None and row['valid'] is True and row['ready'] is True
            and row['unique'] is False and row['plain'] is True
            and row['method']=='btree' and row['table_schema']=='public'
            and row['table_name']=='contratos_procesados'
            and row['key_count']==row['column_count']==2
            and tuple(row['columns'])==COLUMNS and tuple(row['option_flags'])==(0,0))


def upgrade():
    with op.get_context().autocommit_block():
        current=_index()
        if current is None:
            op.create_index(NAME,'contratos_procesados',list(COLUMNS),unique=False,
                            schema='public',postgresql_concurrently=True)
            current=_index()
        if not _matches(current):
            raise RuntimeError('El índice de paginación no coincide o está inválido; conservar y revisar')


def downgrade():
    with op.get_context().autocommit_block():
        current=_index()
        if current is None:
            return
        if not _matches(current):
            raise RuntimeError('El índice de paginación no coincide; conservar y revisar')
        op.drop_index(NAME,table_name='contratos_procesados',schema='public',
                      postgresql_concurrently=True)
