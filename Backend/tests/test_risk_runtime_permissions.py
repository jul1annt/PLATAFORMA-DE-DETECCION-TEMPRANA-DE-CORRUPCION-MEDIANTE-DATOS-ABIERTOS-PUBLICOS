"""Startup must cover dispatch, ingestion and normalization as well as risk."""
import pytest

from modules.motor_riesgo.runtime_permissions import missing_runtime_permissions


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class PermissionSession:
    def __init__(self, denied=(), without_sequence=()):
        self.denied = set(denied)
        self.without_sequence = set(without_sequence)
        self.checked = set()

    def execute(self, statement, params):
        sql = str(statement)
        if 'pg_get_serial_sequence' in sql:
            table = params['table_name']
            return ScalarResult(None if table in self.without_sequence else table + '_id_seq')
        kind = next(kind for kind in ('schema', 'table', 'sequence')
                    if 'has_' + kind + '_privilege' in sql)
        key = (kind, params['name'], params['privilege'])
        self.checked.add(key)
        return ScalarResult(key not in self.denied)


@pytest.mark.parametrize('kind,name,privilege', [
    ('table', 'public.background_jobs', 'SELECT'),
    ('table', 'public.background_jobs', 'INSERT'),
    ('table', 'public.background_jobs', 'UPDATE'),
    ('table', 'public.fuentes_datos', 'SELECT'),
    ('table', 'public.fuentes_datos', 'UPDATE'),
    ('table', 'public.raw_secop_historial', 'INSERT'),
    ('table', 'public.sincronizacion_historial', 'INSERT'),
    ('table', 'public.sincronizacion_historial', 'UPDATE'),
    ('sequence', 'public.background_jobs_id_seq', 'USAGE'),
    ('sequence', 'public.raw_secop_id_seq', 'USAGE'),
    ('sequence', 'public.raw_secop_historial_id_seq', 'USAGE'),
    ('sequence', 'public.sincronizacion_historial_id_seq', 'USAGE'),
    ('sequence', 'public.contratos_procesados_id_seq', 'USAGE'),
    ('sequence', 'public.contrato_anomalo_incompleto_id_seq', 'USAGE'),
    ('sequence', 'public.estadistica_campos_faltantes_id_seq', 'USAGE'),
])
def test_missing_daily_pipeline_permission_is_reported(kind, name, privilege):
    session = PermissionSession(denied=[(kind, name, privilege)])
    assert missing_runtime_permissions(session) == [
        {'kind': kind, 'object': name, 'privilege': privilege}
    ]


def test_all_permissions_present_and_no_new_delete_access_required():
    session = PermissionSession()
    assert missing_runtime_permissions(session) == []
    for table in ('background_jobs', 'fuentes_datos', 'raw_secop_historial',
                  'sincronizacion_historial'):
        assert ('table', 'public.' + table, 'DELETE') not in session.checked
    assert ('table', 'public.fuentes_datos', 'INSERT') not in session.checked


def test_tables_without_serial_sequence_are_not_assumed_to_have_one():
    table = 'public.contratos_metricas_calidad'
    session = PermissionSession(without_sequence=[table])
    assert missing_runtime_permissions(session) == []
    assert not any(kind == 'sequence' and name == table + '_id_seq'
                   for kind, name, _ in session.checked)
