"""Maintain exact quality totals in the same transaction as contract changes."""
from alembic import op
import sqlalchemy as sa

revision = '2ab7c4e8d910'
down_revision = '08c6d9a2e4b1'
branch_labels = None
depends_on = None

TABLE = 'contratos_metricas_calidad'
CONTRACTS = 'contratos_procesados'
FIELDS = 'es_incompleto,es_sospechoso,clasificacion_riesgo,nivel_confianza'


def _function(event):
    if event == 'update':
        # ORM executemany sends one UPDATE per row. Direct deltas avoid building
        # and aggregating transition relations for every small statement.
        return f"""
        CREATE FUNCTION public.apply_contract_quality_update() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
        DECLARE
            d_incomplete integer; d_suspicious integer; d_high integer;
            d_known integer; d_sum numeric;
        BEGIN
            d_incomplete := (NEW.es_incompleto IS TRUE)::integer - (OLD.es_incompleto IS TRUE)::integer;
            d_suspicious := (NEW.es_sospechoso IS TRUE)::integer - (OLD.es_sospechoso IS TRUE)::integer;
            d_high := ((NEW.clasificacion_riesgo='ALTO') IS TRUE)::integer - ((OLD.clasificacion_riesgo='ALTO') IS TRUE)::integer;
            d_known := (NEW.nivel_confianza IS NOT NULL)::integer - (OLD.nivel_confianza IS NOT NULL)::integer;
            d_sum := coalesce(NEW.nivel_confianza::numeric,0) - coalesce(OLD.nivel_confianza::numeric,0);
            UPDATE public.{TABLE}
            SET incompletos=incompletos+d_incomplete,sospechosos=sospechosos+d_suspicious,
                alto_riesgo=alto_riesgo+d_high,con_confianza=con_confianza+d_known,
                suma_confianza=suma_confianza+d_sum WHERE id=1;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Missing transactional contract quality summary'
                    USING ERRCODE='integrity_constraint_violation';
            END IF;
            RETURN NULL;
        END; $$
        """
    relations = []
    if event in ('insert', 'update'):
        relations.append(f'SELECT 1 AS direction,{FIELDS} FROM new_contracts')
    if event in ('delete', 'update'):
        relations.append(f'SELECT -1 AS direction,{FIELDS} FROM old_contracts')
    changes = ' UNION ALL '.join(relations)
    return f"""
    CREATE FUNCTION public.apply_contract_quality_{event}() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
    DECLARE
        d_total bigint; d_incomplete bigint; d_suspicious bigint; d_high bigint;
        d_known bigint; d_sum numeric;
    BEGIN
        SELECT coalesce(sum(direction),0),
               coalesce(sum(direction) FILTER (WHERE es_incompleto IS TRUE),0),
               coalesce(sum(direction) FILTER (WHERE es_sospechoso IS TRUE),0),
               coalesce(sum(direction) FILTER (WHERE clasificacion_riesgo='ALTO'),0),
               coalesce(sum(direction) FILTER (WHERE nivel_confianza IS NOT NULL),0),
               coalesce(sum(nivel_confianza::numeric * direction),0)
        INTO d_total,d_incomplete,d_suspicious,d_high,d_known,d_sum
        FROM ({changes}) changes;
        IF d_total<>0 OR d_incomplete<>0 OR d_suspicious<>0 OR d_high<>0 OR d_known<>0 OR d_sum<>0 THEN
            UPDATE public.{TABLE}
            SET total=total+d_total,incompletos=incompletos+d_incomplete,
                sospechosos=sospechosos+d_suspicious,alto_riesgo=alto_riesgo+d_high,
                con_confianza=con_confianza+d_known,suma_confianza=suma_confianza+d_sum
            WHERE id=1;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Missing transactional contract quality summary'
                    USING ERRCODE='integrity_constraint_violation';
            END IF;
        END IF;
        RETURN NULL;
    END; $$
    """


def upgrade():
    # Read Committed obtains a fresh snapshot after waiting for prior writers.
    # Bound waiting and backfill; a failure rolls back table/functions/triggers.
    op.execute("""DO $$ BEGIN
        IF current_setting('transaction_isolation') <> 'read committed' THEN
            RAISE EXCEPTION 'Contract quality initialization requires read committed';
        END IF;
    END; $$""")
    op.execute("SET LOCAL lock_timeout='5s'")
    op.execute("SET LOCAL statement_timeout='120s'")
    op.create_table(
        TABLE,
        sa.Column('id', sa.SmallInteger(), nullable=False),
        *[sa.Column(name, sa.BigInteger(), nullable=False, server_default=sa.text('0')) for name in ('total','incompletos','sospechosos','alto_riesgo','con_confianza')],
        sa.Column('suma_confianza', sa.Numeric(38,0), nullable=False, server_default=sa.text('0')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('id = 1',name='ck_cmc_singleton'),
        sa.CheckConstraint('total >= 0 AND incompletos BETWEEN 0 AND total AND sospechosos BETWEEN 0 AND total AND alto_riesgo BETWEEN 0 AND total AND con_confianza BETWEEN 0 AND total',name='ck_cmc_counts'),
        schema='public',
    )
    op.execute(f'LOCK TABLE public.{CONTRACTS} IN SHARE ROW EXCLUSIVE MODE')
    op.execute(f"""INSERT INTO public.{TABLE} (id,total,incompletos,sospechosos,alto_riesgo,con_confianza,suma_confianza)
        SELECT 1,count(*),count(*) FILTER (WHERE es_incompleto IS TRUE),
               count(*) FILTER (WHERE es_sospechoso IS TRUE),
               count(*) FILTER (WHERE clasificacion_riesgo='ALTO'),
               count(nivel_confianza),coalesce(sum(nivel_confianza::numeric),0)
        FROM public.{CONTRACTS}""")
    for event in ('insert','delete'):
        op.execute(_function(event))
        references = []
        if event in ('delete','update'):
            references.append('OLD TABLE AS old_contracts')
        if event in ('insert','update'):
            references.append('NEW TABLE AS new_contracts')
        op.execute(f"""CREATE TRIGGER trg_contract_quality_{event}
            AFTER {event.upper()} ON public.{CONTRACTS}
            REFERENCING {' '.join(references)}
            FOR EACH STATEMENT EXECUTE FUNCTION public.apply_contract_quality_{event}()""")
    op.execute(_function('update'))
    op.execute(f"""CREATE TRIGGER trg_contract_quality_update
        AFTER UPDATE ON public.{CONTRACTS} FOR EACH ROW
        WHEN ((OLD.es_incompleto IS TRUE,OLD.es_sospechoso IS TRUE,
               (OLD.clasificacion_riesgo='ALTO') IS TRUE,OLD.nivel_confianza)
          IS DISTINCT FROM
              (NEW.es_incompleto IS TRUE,NEW.es_sospechoso IS TRUE,
               (NEW.clasificacion_riesgo='ALTO') IS TRUE,NEW.nivel_confianza))
        EXECUTE FUNCTION public.apply_contract_quality_update()""")
    op.execute(f"""CREATE FUNCTION public.apply_contract_quality_truncate() RETURNS trigger
        LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
        BEGIN
            UPDATE public.{TABLE} SET total=0,incompletos=0,sospechosos=0,
                alto_riesgo=0,con_confianza=0,suma_confianza=0 WHERE id=1;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'Missing transactional contract quality summary'
                    USING ERRCODE='integrity_constraint_violation';
            END IF;
            RETURN NULL;
        END; $$""")
    op.execute(f"""CREATE TRIGGER trg_contract_quality_truncate
        AFTER TRUNCATE ON public.{CONTRACTS} FOR EACH STATEMENT
        EXECUTE FUNCTION public.apply_contract_quality_truncate()""")


def downgrade():
    for event in ('insert','update','delete','truncate'):
        op.execute(f'DROP TRIGGER trg_contract_quality_{event} ON public.{CONTRACTS}')
        op.execute(f'DROP FUNCTION public.apply_contract_quality_{event}()')
    op.drop_table(TABLE, schema='public')
