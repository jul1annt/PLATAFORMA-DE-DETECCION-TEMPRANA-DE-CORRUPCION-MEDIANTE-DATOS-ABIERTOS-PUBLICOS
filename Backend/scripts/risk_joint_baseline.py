"""Compose frozen local IQR and rolling inputs; no database access or publication."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.motor_riesgo.joint_baseline import assess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    with manifest_path.open('rb') as stream:
        body = stream.read(1024 * 1024 + 1)
    if len(body) > 1024 * 1024:
        raise ValueError('Manifiesto demasiado grande')
    manifest = json.loads(body)
    if (manifest.get('version') != 'joint-baseline-input-v1' or not isinstance(manifest['histories'], list)
            or len(manifest['histories']) > 1000):
        raise ValueError('Manifiesto de composición inválido')
    seen, provenance, total = set(), [], 0
    def read(entry):
        nonlocal total
        relative = Path(entry['path'])
        if relative.is_absolute() or relative.drive or '..' in relative.parts:
            raise ValueError('Ruta debe permanecer en el directorio del manifiesto')
        path = (manifest_path.parent / relative).resolve()
        expected = entry['sha256']
        if (not path.is_relative_to(manifest_path.parent) or path in seen
                or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
            raise ValueError('Ruta repetida, externa o hash inválido')
        seen.add(path)
        with path.open('rb') as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        total += len(raw)
        if (len(raw) > 16 * 1024 * 1024 or total > 256 * 1024 * 1024
                or hashlib.sha256(raw).hexdigest() != expected):
            raise ValueError('Tamaño o hash de entrada incompatible')
        provenance.append({'path': entry['path'], 'sha256': expected})
        return json.loads(raw)
    cohort = read(manifest['cohort'])
    report = assess(cohort, (read(entry) for entry in manifest['histories']))
    report['input_manifest_sha256'] = hashlib.sha256(body).hexdigest()
    report['input_files'] = provenance
    paths = [Path(__file__), *(BACKEND / 'modules/motor_riesgo' / name for name in
              ('joint_baseline.py', 'cut_rules.py', 'rolling_evidence.py', 'rules.py',
               'baseline_coverage.py', 'weight_lab.py', 'domain.py', 'robust_priority.py'))]
    report['implementation_sha256'] = {str(path.relative_to(BACKEND)).replace('\\', '/'):
                                       hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False); out.write('\n')
    print(json.dumps({key: report[key] for key in ('targets', 'histories_supplied', 'histories_accepted',
                                                  'complete_descriptive_counts', 'publication_authorized')}))


if __name__ == '__main__':
    main()
