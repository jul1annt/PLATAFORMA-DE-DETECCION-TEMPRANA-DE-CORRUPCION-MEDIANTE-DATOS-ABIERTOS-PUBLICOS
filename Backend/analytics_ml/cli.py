"""File protocol for isolated model processes. No DB or API imports."""
import argparse
import json
import hashlib
import platform
from pathlib import Path
from .corpus import verified_cases, prepare_rows
from .inference import validate_artifact, predict, PreparedPredictor
from .streams import binary_stream, physical_sha256
from .evidence import verified_observations
from .runtime import prediction_code_sha256
from modules.motor_riesgo.domain import STAGES, FEATURE_VERSION, digest


def write_new(path: Path, value):
    with path.open('x', encoding='utf-8') as out:
        json.dump(value, out, ensure_ascii=False, sort_keys=True, allow_nan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('inventory', 'train'):
        item = sub.add_parser(command)
        item.add_argument('--cases', type=Path, required=True)
        item.add_argument('--evidence', type=Path, required=True)
        item.add_argument('--feature-evidence', type=Path, required=True)
        item.add_argument('--observations', type=Path, required=True)
        item.add_argument('--output', type=Path, required=True)
        item.add_argument('--version', default='candidate')
    item = sub.add_parser('infer')
    model_input = item.add_mutually_exclusive_group(required=True)
    model_input.add_argument('--model', type=Path)
    model_input.add_argument('--models', type=Path)
    item.add_argument('--observations', type=Path, required=True)
    item.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'infer':
        if args.models:
            models = json.loads(args.models.read_text(encoding='utf-8'))
            if set(models) != set(STAGES):
                raise ValueError('La inferencia conjunta requiere los dos modelos independientes')
        else:
            model = json.loads(args.model.read_text(encoding='utf-8'))
            models = {model['stage']: model}
        prepared = {}
        for stage, model in models.items():
            validate_artifact(model)
            if model['stage'] != stage:
                raise ValueError('El artefacto no corresponde a la etapa declarada')
            prepared[stage] = PreparedPredictor(model)
        checksum = hashlib.sha256()
        counts = {stage: 0 for stage in models}
        evaluated_counts = {stage: 0 for stage in models}
        input_rows = 0
        with binary_stream(args.output, 'xb') as out, binary_stream(args.observations, 'rb') as source:
            for line in source:
                checksum.update(line)
                input_rows += 1
                observation = json.loads(line)
                stage = observation['stage']
                if stage not in STAGES:
                    raise ValueError('Etapa de observación desconocida')
                if stage in models:
                    result = predict(models[stage], observation, prepared[stage].score)
                    out.write((json.dumps({'raw_secop_id': observation['raw_secop_id'], 'stage': stage, 'result': result},
                                          ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8'))
                    counts[stage] += 1
                    evaluated_counts[stage] += int(result['index'] is not None)
        with args.output.open('rb') as artifact:
            output_hash = hashlib.file_digest(artifact, 'sha256').hexdigest()
        write_new(Path(str(args.output)+'.manifest.json'), {'input_rows': input_rows, 'counts': counts,'evaluated_counts':evaluated_counts,
            'observations_sha256': checksum.hexdigest(), 'hash_scope': 'uncompressed_jsonl_bytes',
            'models_sha256': {stage: model['sha256'] for stage, model in models.items()},
            'output_sha256': output_hash, 'output_bytes': args.output.stat().st_size,
            'python': platform.python_version(), 'feature_version': FEATURE_VERSION,
            'prediction_code_sha256':prediction_code_sha256(),
            'code_sha256': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                            for name in ('cli.py','inference.py','streams.py')}})
        return
    case_records = json.loads(args.cases.read_text(encoding='utf-8'))
    feature_registry = json.loads(args.feature_evidence.read_text(encoding='utf-8'))
    cases, inventory = verified_cases(case_records, args.evidence)
    observations = []
    checksum = hashlib.sha256()
    logical_size = 0
    with binary_stream(args.observations, 'rb') as source:
        for line in source:
            checksum.update(line)
            logical_size += len(line)
            if logical_size > 512 * 1024**2:
                raise ValueError('Máximo de entrenamiento: 512 MiB descomprimidos')
            observations.append(json.loads(line))
            if len(observations) > 200000:
                raise ValueError('Máximo de entrenamiento: 200000 observaciones. Preparar muestra estratificada versionada.')
    observations, feature_evidence = verified_observations(observations, feature_registry, args.evidence)
    outputs = {}
    for stage in ('CONVOCATORIA', 'ADJUDICACION'):
        rows, coverage = prepare_rows(observations, cases, stage)
        item = {'coverage': coverage}
        if args.command == 'train':
            from .training import train
            try:
                receipt = {'policy': feature_evidence['policy'], 'registry_sha256': feature_evidence['registry_sha256'],
                           'verified_rows': len(rows), 'verified_dataset_sha256': digest(rows)}
                artifact, report = train(rows, stage, args.version + '-' + stage.lower(), evidence=receipt)
                item.update(artifact=artifact, report=report)
            except ValueError as exc:
                item.update(blocked=True, reason=str(exc))
        outputs[stage] = item
    write_new(args.output, {'inventory': inventory, 'stages': outputs, 'feature_evidence': feature_evidence,
              'inputs': {'observations_sha256': checksum.hexdigest(), 'observations_file_sha256': physical_sha256(args.observations),
                         'cases_sha256': digest(case_records), 'feature_evidence_sha256': digest(feature_registry)}})
    print(json.dumps({'command': args.command, 'eligible_cases': len(cases), 'stages': {k: v['coverage'] for k,v in outputs.items()}}))


if __name__ == '__main__':
    main()
