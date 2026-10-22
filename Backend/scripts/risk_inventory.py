"""Reproducible first deliverable: candidates are not presumed training labels."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analytics_ml.corpus import verified_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    _, inventory = verified_cases(json.loads(args.cases.read_text(encoding='utf-8')), args.evidence)
    inventory.update(scope='Inventario inicial de descubrimiento, no búsqueda exhaustiva de todas las sentencias colombianas.',
                     training_performed=False, judicial_labels_invented=False, publication_authorized=False)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(inventory, out, indent=2, ensure_ascii=False)
        out.write('\n')
    print(json.dumps({'candidates': inventory['candidates'], 'eligible_cases': inventory['eligible_cases']}))


if __name__ == '__main__':
    main()
