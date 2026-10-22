"""Atomic reusable batch output; incomplete attempts never replace a run."""
import json
from pathlib import Path
from uuid import uuid4
from analytics_ml.runtime import prediction_code_sha256
from analytics_ml.streams import physical_sha256
from .domain import STAGES,FEATURE_VERSION


def verify_output(output: Path,manifest: dict,context: dict,artifacts: dict):
    if (manifest.get('observations_sha256')!=context['observations_sha256']
            or manifest.get('counts')!=context['counts']
            or manifest.get('models_sha256')!={stage:a['sha256'] for stage,a in artifacts.items()}
            or manifest.get('input_rows')!=sum(context['counts'].values())
            or manifest.get('feature_version')!=FEATURE_VERSION
            or manifest.get('prediction_code_sha256')!=prediction_code_sha256()):
        raise ValueError('La inferencia no corresponde a insumos, modelos e implementación congelados')
    evaluated=manifest.get('evaluated_counts',{})
    if set(evaluated)!=set(STAGES) or any(type(evaluated[s]) is not int or not 0<=evaluated[s]<=manifest['counts'][s] for s in STAGES):
        raise ValueError('Cobertura evaluable de inferencia inválida')
    if not output.is_file() or physical_sha256(output)!=manifest.get('output_sha256'):
        raise ValueError('El resultado de inferencia cambió antes de persistirlo')


def completed_inference(directory: Path,observations: Path,context: dict,artifacts: dict,interpreter: str):
    from .service import run_process
    completed=directory/'inference-complete'
    if not completed.exists():
        attempt=directory/('inference-attempt-'+uuid4().hex)
        attempt.mkdir()
        models=attempt/'models.json'
        models.write_text(json.dumps(artifacts,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        output=attempt/'results.jsonl.gz'
        run_process(interpreter,['infer','--models',str(models),'--observations',str(observations),'--output',str(output)])
        manifest=json.loads(Path(str(output)+'.manifest.json').read_text(encoding='utf-8'))
        verify_output(output,manifest,context,artifacts)
        # A directory rename on the same filesystem makes the output and its
        # verified manifest visible together. Interrupted attempts are retained.
        attempt.rename(completed)
    output=completed/'results.jsonl.gz'
    manifest=json.loads(Path(str(output)+'.manifest.json').read_text(encoding='utf-8'))
    verify_output(output,manifest,context,artifacts)
    return output,manifest
