"""Audit stored SECOP response fields with frozen official semantic evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.motor_riesgo.competition_context import assess, FIELDS, DATASET


def read(path, limit):
    with path.open('rb') as stream:
        body = stream.read(limit + 1)
    if len(body) > limit: raise ValueError('Archivo demasiado grande')
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = read(args.input, 16 * 1024 * 1024)
    source_manifest = args.source_manifest.resolve()
    source_body = read(source_manifest, 1024 * 1024)
    sources = json.loads(source_body)
    if not isinstance(sources, list) or len(sources) != 3:
        raise ValueError('Se requieren los dos diccionarios y la metadata de fuente congelados')
    evidence, metadata = [], None
    names = set()
    for source in sources:
        relative = Path(source['file'])
        path = (source_manifest.parent / relative).resolve()
        if (relative.is_absolute() or relative.drive or '..' in relative.parts
                or not path.is_relative_to(source_manifest.parent) or path in names or source.get('status') != 200):
            raise ValueError('Evidencia no admisible')
        names.add(path)
        body = read(path, 20 * 1024 * 1024)
        if hashlib.sha256(body).hexdigest() != source['sha256']:
            raise ValueError('Hash de evidencia incompatible')
        if path.name == 'dataset_metadata.json': metadata = json.loads(body)
        evidence.append({'file': source['file'], 'sha256': source['sha256'], 'url': source['url']})
    if metadata is None or metadata.get('id') != DATASET or not set(FIELDS) <= {field.get('fieldName') for field in metadata['columns']}:
        raise ValueError('Metadata sin campos necesarios para esta auditoría')
    report = assess(json.loads(raw))
    report['input_sha256'] = hashlib.sha256(raw).hexdigest()
    report['source_manifest_sha256'] = hashlib.sha256(source_body).hexdigest()
    report['reviewed_sources'] = evidence
    report['metadata_field_profiles'] = [{'fieldName': column['fieldName'], 'dataTypeName': column.get('dataTypeName'),
                                          'definition_sha256': hashlib.sha256(str(column.get('description') or '').encode()).hexdigest(),
                                          'accepted_as_actual_bidder_feature': False}
                                         for column in metadata['columns'] if column.get('fieldName') in FIELDS]
    paths = [Path(__file__), BACKEND / 'modules/__init__.py', *(BACKEND / 'modules/motor_riesgo' / name for name in
              ('__init__.py', 'competition_context.py', 'method_reference.py', 'baseline_coverage.py', 'domain.py'))]
    report['implementation_sha256'] = {str(path.relative_to(BACKEND)).replace('\\', '/'):
                                       hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False); out.write('\n')
    print(json.dumps({'rows': len(report['results']), 'summary': report['summary'],
                      'actual_bidder_fallback_enabled': False, 'weight_changes': False}))


if __name__ == '__main__': main()
