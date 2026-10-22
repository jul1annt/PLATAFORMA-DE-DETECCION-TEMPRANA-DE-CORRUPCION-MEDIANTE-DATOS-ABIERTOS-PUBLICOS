"""Offline buyer-year coverage and process participation; no new database reads."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BACKEND=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BACKEND))
from modules.motor_riesgo.annual_context import assess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with args.input.open('rb') as stream:body=stream.read(16*1024*1024+1)
    if len(body)>16*1024*1024:raise ValueError('Entrada superior a 16 MiB')
    data=json.loads(body);scope=data['scope']
    complete=scope.get('full_temporally_relevant_exact_stored_buyer_key_frame')
    if type(complete) is not bool or type(scope.get('rows')) is not int or scope['rows']!=len(data['rows']):
        raise ValueError('Completitud y número de filas deben ser explícitos')
    result=assess(data['rows'],data['target'],data['at'],frame_complete=complete)
    report={'scope':scope,'anchor_at':data['at'],'target_contract_id':scope.get('target_contract_id'),
            'temporal_scope':'current_cut_descriptive_not_stage_prediction','assessment':result,
            'input_sha256':hashlib.sha256(body).hexdigest(),'training_eligible':False,'publication_authorized':False,
            'limitations':['Marco de clave almacenada y fuentes locales, no contratación nacional ni mercado económico.',
                           'Procesos observados e identidades conocidas no se usan como denominador completo cuando hay incertidumbre.',
                           'No reconstruye conocimiento histórico ni habilita un predictor entrenado.',
                           'No calcula cuota monetaria, HHI o probabilidad de corrupción.']}
    paths=[Path(__file__),BACKEND/'modules/__init__.py',*(BACKEND/'modules/motor_riesgo'/name for name in ('__init__.py','annual_context.py','domain.py'))]
    report['implementation_sha256']={str(path.relative_to(BACKEND)).replace('\\','/'):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    with args.output.open('x',encoding='utf-8') as out:json.dump(report,out,ensure_ascii=False,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps(result))


if __name__=='__main__':main()
