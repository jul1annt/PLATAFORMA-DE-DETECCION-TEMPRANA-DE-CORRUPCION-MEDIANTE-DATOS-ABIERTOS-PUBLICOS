"""Offline rolling-context diagnostics; never reads a database or activates models."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.motor_riesgo.rolling_evidence import assess
from modules.motor_riesgo.baseline_coverage import baseline_coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with args.input.open('rb') as stream:
        body = stream.read(16 * 1024 * 1024 + 1)
    if len(body) > 16 * 1024 * 1024:
        raise ValueError('Entrada superior a 16 MiB')
    report = assess(json.loads(body))
    report['coverage'] = baseline_coverage(report['values'], 'ADJUDICACION')
    report['input_sha256'] = hashlib.sha256(body).hexdigest()
    paths = [Path(__file__), *(BACKEND / 'modules/motor_riesgo' / name for name in
              ('rolling_evidence.py', 'cut_rules.py', 'rules.py', 'baseline_coverage.py', 'weight_lab.py', 'domain.py'))]
    report['implementation_sha256'] = {str(path.relative_to(BACKEND)).replace('\\', '/'):
                                       hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'values': report['values'], 'training_eligible': False, 'publication_authorized': False}))


if __name__ == '__main__':
    main()
