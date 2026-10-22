"""Transactional source revisions avoid repeated multi-million-row signatures."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
import uuid

revision = 'bd71c6a4046f'
down_revision = '8a6e21c9d430'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('riesgo_versiones_datos',
        sa.Column('table_name', sa.String(60), primary_key=True),
        sa.Column('epoch', pg.UUID(as_uuid=True), nullable=False),
        sa.Column('revision', sa.BigInteger(), nullable=False),
        sa.Column('row_count', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('row_count>=0 AND revision>=0', name='ck_riesgo_versiones_nonnegative'))
    # One initial count under a write fence; triggers and counters become visible
    # in the same migration commit. No source rows are changed.
    op.execute('LOCK TABLE raw_secop,contratos_procesados IN SHARE ROW EXCLUSIVE MODE')
    for name in ('raw_secop', 'contratos_procesados'):
        op.execute(f"INSERT INTO riesgo_versiones_datos(table_name,epoch,revision,row_count) SELECT '{name}','{uuid.uuid4()}'::uuid,0,count(*) FROM {name}")
    op.execute('''CREATE FUNCTION public.riesgo_incrementar_version() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
        DECLARE affected bigint; delta bigint;
        BEGIN
            IF TG_OP='INSERT' THEN
                SELECT count(*) INTO affected FROM risk_new_rows;
                delta:=affected;
            ELSIF TG_OP='DELETE' THEN
                SELECT count(*) INTO affected FROM risk_old_rows;
                delta:=-affected;
            ELSIF TG_OP='UPDATE' THEN
                SELECT count(*) INTO affected FROM risk_new_rows;
                delta:=0;
            ELSE
                affected:=1;
                delta:=0;
            END IF;
            IF affected=0 THEN RETURN NULL; END IF;
            UPDATE public.riesgo_versiones_datos SET revision=revision+1,
                row_count=CASE WHEN TG_OP='TRUNCATE' THEN 0 ELSE row_count+delta END,
                updated_at=clock_timestamp() WHERE table_name=TG_TABLE_NAME;
            IF NOT FOUND THEN RAISE EXCEPTION 'Falta el control de versiones analitico'; END IF;
            RETURN NULL;
        END $$''')
    for name in ('raw_secop', 'contratos_procesados'):
        for action, transition in (('INSERT', 'REFERENCING NEW TABLE AS risk_new_rows'),
                ('UPDATE', 'REFERENCING NEW TABLE AS risk_new_rows'),
                ('DELETE', 'REFERENCING OLD TABLE AS risk_old_rows'), ('TRUNCATE', '')):
            op.execute(f'CREATE TRIGGER risk_version_{action.lower()} AFTER {action} ON {name} {transition} FOR EACH STATEMENT EXECUTE FUNCTION public.riesgo_incrementar_version()')


def downgrade():
    op.execute('LOCK TABLE raw_secop,contratos_procesados IN SHARE ROW EXCLUSIVE MODE')
    for name in ('raw_secop', 'contratos_procesados'):
        for action in ('insert','update','delete','truncate'):
            op.execute(f'DROP TRIGGER risk_version_{action} ON {name}')
    op.execute('DROP FUNCTION public.riesgo_incrementar_version()')
    op.drop_table('riesgo_versiones_datos')
