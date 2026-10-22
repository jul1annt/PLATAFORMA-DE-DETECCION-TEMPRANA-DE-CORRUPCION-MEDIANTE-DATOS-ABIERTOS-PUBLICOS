"""Assess corrected rule priorities under missingness and weight sensitivity."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from modules.motor_riesgo.robust_priority import assess


def unique_object(pairs):
    result = {}
    for key,value in pairs:
        if key in result:
            raise ValueError('Clave JSON repetida')
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError('La salida no puede sustituir la entrada')
    with args.input.open('rb') as stream:
        raw = stream.read(64*1024*1024+1)
    if len(raw) > 64*1024*1024:
        raise ValueError('Entrada mayor de 64 MiB')
    report = assess(json.loads(raw,object_pairs_hook=unique_object,
                               parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Número JSON no finito'))))
    report['input_file_sha256'] = hashlib.sha256(raw).hexdigest()
    files = [Path(__file__), *(BACKEND/'modules/motor_riesgo'/name for name in
              ('robust_priority.py','baseline_coverage.py','domain.py'))]
    report['implementation_sha256'] = {str(p.relative_to(BACKEND)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    body = json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    with args.output.open('x',encoding='utf-8') as stream:
        stream.write(body)
    print(json.dumps({key:report[key] for key in ('targets','review_route_counts','fully_resolved_priorities','publication_authorized')}))


if __name__ == '__main__':
    main()
