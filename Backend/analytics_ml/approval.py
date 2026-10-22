"""One approval policy for administrative activation and local startup."""
import math
import re
from modules.motor_riesgo.domain import digest
from .inference import validate_artifact
from .evidence import POLICY
from .evaluation import validate_split_audit
from modules.motor_riesgo.baseline_coverage import POLICY as BASELINE_POLICY


def validate_approval(artifact: dict, report: dict, stage: str, version: str, validated: bool):
    if not validated or artifact.get('stage') != stage:
        raise ValueError('Modelo no validado para la etapa ' + stage)
    validate_artifact(artifact)
    if (report.get('sha256') != digest({k:v for k,v in report.items() if k != 'sha256'})
            or report.get('artifact_sha256') != artifact['sha256']):
        raise ValueError('Integridad del informe inválida')
    if (report.get('stage') != stage or report.get('version') != version or artifact.get('version') != version
            or report.get('positive_target') != 'CORRUPCION' or report.get('validated') is not True):
        raise ValueError('Informe de etapa, objetivo o versión incompatible')
    manifest = report.get('runtime_manifest')
    if not isinstance(manifest, dict) or not manifest or artifact.get('runtime_manifest_sha256') != digest(manifest):
        raise ValueError('Integridad del manifiesto de entrenamiento inválida')
    dataset_hash = artifact.get('dataset_sha256')
    if not isinstance(dataset_hash, str) or not re.fullmatch('[a-f0-9]{64}', dataset_hash) or report.get('dataset_sha256') != dataset_hash:
        raise ValueError('El informe y el modelo corresponden a conjuntos distintos')
    evidence = report.get('feature_evidence', {})
    if (evidence.get('policy') != POLICY or evidence.get('verified_dataset_sha256') != dataset_hash
            or artifact.get('feature_evidence_sha256') != digest(evidence)
            or not re.fullmatch('[a-f0-9]{64}', str(evidence.get('registry_sha256', '')))
            or type(evidence.get('verified_rows')) is not int or evidence['verified_rows'] < 1):
        raise ValueError('La evidencia física revisada no acredita el conjunto evaluado')
    split_audit = report.get('split_audit')
    validate_split_audit(split_audit, report.get('split_sizes'), evidence['verified_rows'])
    if artifact.get('split_audit_sha256') != digest(split_audit):
        raise ValueError('La partición temporal no corresponde al artefacto')
    baseline = report.get('baseline_coverage')
    if (not isinstance(baseline, dict) or baseline.get('policy') != BASELINE_POLICY
            or report.get('baseline_complete_for_comparison') is not True
            or type(baseline.get('complete_rows')) is not int
            or baseline['complete_rows'] != report['split_sizes'][2]
            or type(baseline.get('total_rows')) is not int
            or baseline['total_rows'] != report['split_sizes'][2]
            or not re.fullmatch('[a-f0-9]{64}', str(baseline.get('operation_coverage_sha256', '')))):
        raise ValueError('La comparación de reglas tiene cobertura incompleta o no acreditada')
    counts = report.get('split_case_counts', [])
    if (len(counts) != 3 or any(type(n) is not int or n < 5 for n in counts)
            or any(n > size for n, size in zip(counts, report['split_sizes']))):
        raise ValueError('Cobertura de expedientes insuficiente')
    for interval in (report.get('case_interval', {}), report.get('unseen_suppliers', {})):
        lower = interval.get('lower95')
        if (interval.get('passed') is not True or type(interval.get('cases')) is not int or interval['cases'] < 5
                or type(lower) not in (int,float) or not math.isfinite(lower) or lower <= 0
                or interval.get('method') != 'paired_case_bootstrap_fixed_top5_tie_aware'
                or interval.get('repetitions') != 2000):
            raise ValueError('La evaluación independiente no aprobó')
