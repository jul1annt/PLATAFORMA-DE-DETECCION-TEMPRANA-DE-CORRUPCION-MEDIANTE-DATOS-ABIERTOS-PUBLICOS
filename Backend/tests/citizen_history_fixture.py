"""Remove only before images created by a committed synthetic test workflow."""
from sqlalchemy import event,text


class OwnedCitizenHistory:
    def __init__(self,engine):
        assert engine.url.host in {'127.0.0.1','localhost','::1'} and 'test' in engine.url.database.lower()
        self.engine=engine
        self.transactions=set()
        event.listen(engine,'commit',self.record)

    def record(self,connection):
        # PostgreSQL xmin records the writing transaction. These tests use
        # ordinary committed batches, not independently committed savepoints.
        self.transactions.add(connection.execute(text('SELECT txid_current()%4294967296')).scalar_one())

    def cleanup(self,raw_ids):
        event.remove(self.engine,'commit',self.record)
        with self.engine.begin() as db:
            exists=db.execute(text("SELECT to_regclass('public.riesgo_cortes_ciudadanos') IS NOT NULL")).scalar_one()
            if not exists: return
            assert db.execute(text('SELECT count(*) FROM public.riesgo_cortes_ciudadanos')).scalar_one()==0, 'Never remove history referenced by a public cut'
            assert db.execute(text('SELECT count(*) FROM raw_secop WHERE id=ANY(:ids)'),{'ids':list(raw_ids)}).scalar_one()==0
            for table in ('contratos_procesados','contrato_anomalo_incompleto','contratos_metricas_calidad','estadistica_campos_faltantes'):
                sql='DELETE FROM riesgo_historial.'+table+' WHERE xmin::text::bigint=ANY(:owned)'
                if table in {'contratos_procesados','contrato_anomalo_incompleto'}:
                    sql+=' AND raw_secop_id=ANY(:ids)'
                db.execute(text(sql),{'owned':list(self.transactions),'ids':list(raw_ids)})
