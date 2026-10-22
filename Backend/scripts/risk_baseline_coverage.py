"""Offline baseline diagnostics from prepared stage observations; never publishes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.motor_riesgo.rules import chronological_baseline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.input.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('Entrada superior a 16 MiB; separar en cortes explícitos')
    body = args.input.read_bytes()
    if len(body) > 16 * 1024 * 1024:
        raise ValueError('Entrada superior a 16 MiB')
    payload = json.loads(body)
    if (not isinstance(payload, dict) or not isinstance(payload.get('history'), list)
            or not isinstance(payload.get('targets'), list)
            or len(payload['history']) + len(payload['targets']) > 10000):
        raise ValueError('Se requieren history y targets, máximo 10000 observaciones en conjunto')
    scores, coverage = chronological_baseline(payload['history'], payload['targets'], payload['stage'])
    paths = [Path(__file__), BACKEND / 'modules/motor_riesgo/rules.py',
             BACKEND / 'modules/motor_riesgo/baseline_coverage.py', BACKEND / 'modules/motor_riesgo/domain.py']
    result = {'stage': payload['stage'], 'scores_lower_bound': scores, 'coverage': coverage,
              'target_order': 'Mismo orden que targets en el archivo de entrada; no deduplicar resultados por nombre.',
              'input_sha256': hashlib.sha256(body).hexdigest(),
              'implementation_sha256': {str(p.relative_to(BACKEND)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
              'scope': 'Diagnóstico de variables preparadas; no acredita revisión documental, identidad SECOP o ausencia de futuro en los datos de entrada.',
              'database_accessed': False, 'training_performed': False, 'publication_authorized': False}
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'rows': len(scores), 'complete_rows': coverage['complete_rows'], 'publication_authorized': False}))


if __name__ == '__main__':
    main()
