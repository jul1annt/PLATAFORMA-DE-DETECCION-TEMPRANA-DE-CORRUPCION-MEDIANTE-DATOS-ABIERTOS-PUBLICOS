"""Read-only gate for optional Windows startup. Never enables a pending model."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from scripts.local_integration import configuration,validate_database_identity,read_json


def check_inference_environment(backend, api_python, environment):
    """Probe the selected package with each real interpreter before startup.

    Daily inference does not require starting the independent training runtime.
    No database credentials are passed to either probe.
    """
    from modules.motor_riesgo.process_runner import bounded_run
    from analytics_ml.runtime import prediction_code_sha256
    probe = backend / 'scripts/risk_inference_probe.py'
    if not probe.is_file():
        raise ValueError('El paquete no incluye la comprobación de inferencia')
    inference_python = Path(environment.get('RISK_INFERENCE_PYTHON', ''))
    if not inference_python.is_absolute() or not inference_python.is_file():
        raise ValueError('Configurar el intérprete aislado de inferencia antes del inicio')
    operating_system_keys = {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP',
                             'SYSTEMDRIVE', 'COMSPEC', 'PATHEXT', 'LANG', 'LC_ALL', 'TZ'}
    safe_environment = {key: value for key, value in environment.items()
                        if key.upper() in operating_system_keys}
    safe_environment.update(PYTHONNOUSERSITE='1', PYTHONIOENCODING='utf-8',
                            OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    reports = []
    for interpreter in (Path(api_python), inference_python):
        if not interpreter.is_absolute() or not interpreter.is_file():
            raise ValueError('Intérprete del paquete no disponible')
        result = bounded_run([str(interpreter), '-I', str(probe)],
                             cwd=backend, env=safe_environment, timeout=30)
        if result.returncode:
            raise ValueError('El intérprete no pudo cargar la inferencia del paquete')
        try:
            report = json.loads(result.stdout)
            if (report['isolated'] != 1 or report['training_dependencies_loaded'] is not False
                    or report['prediction_code_sha256'] != prediction_code_sha256()
                    or not Path(report['prefix']).is_absolute()
                    or not Path(report['base_prefix']).is_absolute()):
                raise ValueError('Entorno de inferencia incompatible con el paquete')
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError('Respuesta inválida de la comprobación de inferencia') from exc
        reports.append(report)
    api, inference = reports
    prefix = Path(inference['prefix']).resolve()
    if prefix == Path(api['prefix']).resolve() or prefix == Path(inference['base_prefix']).resolve():
        raise ValueError('La inferencia requiere un entorno virtual separado de la API')
    return {'isolated': True, 'separate_api_environment': True,
            'training_dependencies_loaded': False,
            'prediction_code_sha256': inference['prediction_code_sha256']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve()
    release,backend,_,api_python,environment=configuration(root)
    if not (backend/'modules/motor_riesgo/service.py').is_file():
        raise SystemExit('El paquete publicado aún no incluye el motor validado')
    sys.path.insert(0,str(backend))
    from analytics_ml.approval import validate_approval
    import analytics_ml.approval as approval_module
    if not Path(approval_module.__file__).resolve().is_relative_to(backend.resolve()):
        raise SystemExit('La política de aprobación no corresponde al paquete publicado')
    try:
        inference_check = check_inference_environment(backend, api_python, environment)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    values=dotenv_values(root/'runtime.env')
    engine=create_engine(URL.create('postgresql',username=values['DB_USER'],password=values['DB_PASSWORD'],host=values['DB_HOST'],port=int(values['DB_PORT']),database=values['DB_NAME']),hide_parameters=True,connect_args={'connect_timeout':15})
    try:
        with engine.connect() as db:
            db.execute(text('SET TRANSACTION READ ONLY'))
            identity=tuple(db.execute(text('SELECT current_database(),inet_server_port(),current_user,(SELECT oid FROM pg_database WHERE datname=current_database()),(SELECT version_num FROM alembic_version)')).one())
            flags=dict(db.execute(text('SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication FROM pg_roles WHERE rolname=current_user')).mappings().one())
            validate_database_identity(identity,flags,read_json(root/'provision.json'))
            publication=db.execute(text('SELECT model_ids,daily_enabled FROM riesgo_publicacion WHERE id=1')).mappings().one()
            ids=publication['model_ids']
            if not publication['daily_enabled'] or set(ids)!={'CONVOCATORIA','ADJUDICACION'}:
                raise SystemExit('Se requieren los dos modelos aprobados y actualización diaria habilitada')
            for stage,model_id in ids.items():
                model=db.execute(text('SELECT stage,version,artifact,report,validated FROM riesgo_modelos WHERE id::text=:id'),{'id':model_id}).mappings().one()
                if model['stage']!=stage:
                    raise SystemExit('Modelo asociado a una etapa distinta')
                validate_approval(model['artifact'],model['report'],stage,model['version'],model['validated'])
            from modules.motor_riesgo.public_aggregates import validate_aggregates
            snapshot=db.execute(text('''SELECT s.revision,s.aggregates,s.risk_cut_id,p.cut_id
                FROM riesgo_publicacion_ciudadana c JOIN riesgo_cortes_ciudadanos s ON s.id=c.snapshot_id
                CROSS JOIN riesgo_publicacion p WHERE c.id=1 AND p.id=1''')).mappings().one()
            validate_aggregates(snapshot['aggregates'],snapshot['revision'])
            if snapshot['risk_cut_id']!=snapshot['cut_id']:
                raise SystemExit('Los punteros ciudadanos y analíticos no corresponden al mismo corte')
            from modules.motor_riesgo.runtime_permissions import missing_runtime_permissions
            if missing_runtime_permissions(db):
                raise SystemExit('Faltan permisos del rol operativo para los cortes, sus historiales o el procesamiento')
    finally:
        engine.dispose()
    print(json.dumps({'approved':True,'release':release['ref'],'inference_environment':inference_check}))


if __name__=='__main__':
    main()
