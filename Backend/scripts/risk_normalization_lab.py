"""Compare descriptive normalizations of one frozen legacy results universe."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.motor_riesgo.weight_lab import assess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    if (args.output.resolve() == args.reference.resolve() or args.output.exists() or args.reference.exists()):
        raise ValueError('Se requieren dos salidas nuevas y distintas')
    with args.input.open('rb') as stream:
        body = stream.read(64 * 1024 * 1024 + 1)
    if len(body) > 64 * 1024 * 1024:
        raise ValueError('Entrada superior a 64 MiB')
    report, reference = assess(json.loads(body))
    report['input_sha256'] = hashlib.sha256(body).hexdigest()
    report['implementation_sha256'] = {str(p.relative_to(BACKEND)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in (Path(__file__), BACKEND / 'modules/motor_riesgo/weight_lab.py')}
    for path, value in ((args.reference, reference), (args.output, report)):
        with path.open('x', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write('\n')
    print(json.dumps({'rows': report['rows'], 'variants': len(report['variants']), 'publication_authorized': False}))


if __name__ == '__main__':
    main()
