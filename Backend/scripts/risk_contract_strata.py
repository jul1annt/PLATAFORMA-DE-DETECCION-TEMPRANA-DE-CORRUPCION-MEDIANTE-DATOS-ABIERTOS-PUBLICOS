"""Offline contract-result strata; input must include identity lookup outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.motor_riesgo.contract_strata import assess


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
    report['input_sha256'] = hashlib.sha256(body).hexdigest()
    paths = [Path(__file__), *(BACKEND / 'modules/motor_riesgo' / name for name in ('contract_strata.py', 'weight_lab.py', 'domain.py'))]
    report['implementation_sha256'] = {str(p.relative_to(BACKEND)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(report, out, ensure_ascii=False, indent=2, allow_nan=False)
        out.write('\n')
    print(json.dumps({'input_rows': report['input_rows'], 'eligible_award_units': report['eligible_award_units'], 'excluded_rows': report['excluded_rows']}))


if __name__ == '__main__':
    main()
