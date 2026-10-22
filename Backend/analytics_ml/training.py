"""Optional scikit-learn dependency lives exclusively in the training environment."""
from __future__ import annotations
import random
import statistics
import hashlib
import platform
import re
from pathlib import Path
from importlib.metadata import version as distribution_version
from collections import defaultdict, Counter
from modules.motor_riesgo.domain import NUMERIC, CATEGORICAL, FEATURE_VERSION, PREDICTION_POLICY, digest
from modules.motor_riesgo.rules import chronological_baseline
from .inference import vector, raw_score, validate_artifact
from .evaluation import temporal_split, ranking, paired_case_interval
from .evidence import POLICY
from .runtime import prediction_code_sha256


def runtime_manifest() -> dict:
    """Record actual training dependencies and the implementation used to fit."""
    package = Path(__file__).resolve().parent
    files = [package / name for name in ('training.py', 'inference.py', 'runtime.py', 'corpus.py', 'evaluation.py', 'cli.py', 'streams.py', 'evidence.py', 'approval.py', 'requirements-training.lock')]
    files += [package.parent / 'modules/motor_riesgo' / name for name in (
        'domain.py', 'rules.py', 'baseline_coverage.py', 'feature_builder.py', 'feature_store.py',
        'stage_evidence.py', 'history.py', 'materialize.py', 'method_reference.py',
        'rolling_materialize.py', 'annual_context.py', 'annual_materialize.py')]
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
            'dependencies': {name: distribution_version(name) for name in ('scikit-learn', 'numpy', 'scipy', 'joblib', 'threadpoolctl')},
            'files_sha256': {str(path.relative_to(package.parent)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}}


def fit_transform(rows: list[dict], stage: str) -> dict:
    transform = {'numeric': list(NUMERIC[stage]), 'median': {}, 'mean': {}, 'scale': {}, 'categories': {}}
    for name in NUMERIC[stage]:
        present = [r['values'][name] for r in rows if r['values'][name] is not None]
        median = statistics.median(present) if present else 0.0
        filled = [median if r['values'][name] is None else r['values'][name] for r in rows]
        transform['median'][name] = median
        transform['mean'][name] = statistics.mean(filled)
        transform['scale'][name] = statistics.pstdev(filled) or 1.0
    for name in CATEGORICAL:
        counts = Counter(r['values'][name] for r in rows if r['values'][name] is not None)
        limit = 512 if name == 'categoria' else 100
        transform['categories'][name] = sorted(sorted(counts, key=lambda v: (-counts[v], v))[:limit])
    return transform


def fit(rows: list[dict], stage: str, c: float, *, seed: int, members=25) -> dict:
    from sklearn.linear_model import LogisticRegression
    transform = fit_transform(rows, stage)
    positive = [r for r in rows if r['positive']]
    unlabeled = [r for r in rows if not r['positive']]
    if not positive or not unlabeled:
        raise ValueError('El aprendizaje PU requiere positivos y población sin etiqueta')
    if len(positive) > 10000:
        raise ValueError('Más de 10000 positivos: preparar muestra versionada por expediente antes de entrenar')
    rng = random.Random(seed)
    models = []
    # Each independent case contributes equal total sample weight.
    case_sizes = defaultdict(int)
    for r in positive:
        case_sizes[r['case_group']] += 1
    for index in range(members):
        sampled = rng.choices(unlabeled, k=min(len(unlabeled), max(len(positive) * 5, 100)))
        batch = positive + sampled
        weights = [len(positive) / len(case_sizes) / case_sizes[r['case_group']] for r in positive] + [1.0] * len(sampled)
        model = LogisticRegression(C=c, solver='liblinear', max_iter=2000, random_state=seed + index)
        model.fit([vector(r['values'], transform) for r in batch], [1] * len(positive) + [0] * len(sampled), sample_weight=weights)
        if int(model.n_iter_[0]) >= 2000:
            raise ValueError('El estimador no convergió')
        models.append({'coef': model.coef_[0].tolist(), 'intercept': float(model.intercept_[0])})
    artifact = {'schema': 1, 'stage': stage, 'feature_version': FEATURE_VERSION, 'prediction_policy': PREDICTION_POLICY, 'transform': transform,
                'prediction_code_sha256':prediction_code_sha256(),
                'members': models, 'seed': seed, 'C': c, 'algorithm': 'PU-bagging-logistic-mean-margin', 'reference': [], 'positive_target': 'CORRUPCION'}
    artifact['linear_coef'] = [sum(m['coef'][i] for m in models) / len(models) for i in range(len(models[0]['coef']))]
    artifact['linear_intercept'] = sum(m['intercept'] for m in models) / len(models)
    artifact['reference'] = sorted(raw_score(artifact, r['values'])[0] for r in rows)
    return artifact


def train(rows: list[dict], stage: str, version: str, *, evidence: dict, seed=20261015) -> tuple[dict, dict]:
    if (evidence.get('policy') != POLICY or evidence.get('verified_rows') != len(rows)
            or evidence.get('verified_dataset_sha256') != digest(rows)
            or not re.fullmatch('[a-f0-9]{64}', str(evidence.get('registry_sha256', '')))):
        raise ValueError('La evidencia revisada no corresponde al conjunto de entrenamiento')
    (training, validation, test), split_audit = temporal_split(rows, with_audit=True)
    best = None
    for c in (.1, 1., 10.):
        candidate = fit(training, stage, c, seed=seed)
        scores = [raw_score(candidate, r['values'])[0] for r in validation]
        metric = ranking(validation, scores)['metrics']['0.05']['known_positive_recall']
        if best is None or metric > best[0]:
            best = (metric, candidate)
    artifact = best[1]
    artifact['version'] = version
    artifact['dataset_sha256'] = digest(rows)
    artifact['feature_evidence_sha256'] = digest(evidence)
    artifact['split_audit_sha256'] = digest(split_audit)
    artifact['training_rows'] = len(training)
    manifest = runtime_manifest()
    artifact['runtime_manifest_sha256'] = digest(manifest)
    artifact['sha256'] = digest(artifact)
    validate_artifact(artifact)
    scores = [raw_score(artifact, r['values'])[0] for r in test]
    rules, baseline_coverage = chronological_baseline(training + validation, test, stage)
    # Keep the report bounded: preserve a digest and aggregate coverage rather
    # than embedding every per-operation diagnostic inside the model report.
    operation_coverage = baseline_coverage.pop('operation_coverage')
    baseline_coverage['operation_coverage_sha256'] = digest(operation_coverage)
    del operation_coverage
    baseline_complete = baseline_coverage['complete_rows'] == len(test)
    known_training_suppliers = {r.get('supplier_group') for r in training + validation if r.get('supplier_group')}
    unseen = [i for i, r in enumerate(test) if r.get('supplier_group') and r['supplier_group'] not in known_training_suppliers]
    unseen_rows = [test[i] for i in unseen]
    interval = paired_case_interval(test, scores, rules, seed=seed)
    unseen_interval = paired_case_interval(unseen_rows, [scores[i] for i in unseen], [rules[i] for i in unseen], seed=seed)
    slices = {}
    for dimension in ('periodo', 'modalidad', 'sector_unspsc', 'categoria', 'departamento'):
        groups = defaultdict(list)
        for row, score in zip(test, scores):
            if dimension == 'periodo':
                value = row['prediction_at'][:4]
            elif dimension == 'sector_unspsc':
                match = re.fullmatch(r'(?:V\d+\.)?(\d{8})', str(row['values'].get('categoria') or ''))
                value = match[1][:2] if match else 'SIN_CLASIFICACION_VERIFICABLE'
            else:
                value = row['values'].get(dimension)
            groups[str(value)].append((row, score))
        slices[dimension] = {value: ranking([r for r, _ in group], [s for _, s in group]) for value, group in sorted(groups.items())}
    report = {'stage': stage, 'version': version, 'artifact_sha256': artifact['sha256'], 'dataset_sha256': artifact['dataset_sha256'],
              'positive_target': 'CORRUPCION', 'feature_evidence': evidence,
              'split_sizes': [len(training), len(validation), len(test)], 'split_audit': split_audit,
              'model': ranking(test, scores), 'rules': ranking(test, rules),
              'split_case_counts': [len({r['case_group'] for r in block if r['positive']}) for block in (training,validation,test)],
              'baseline_coverage': baseline_coverage, 'runtime_manifest': manifest,
              'judicial_conducts': {conduct: sum(r.get('case_conduct')==conduct for r in test) for conduct in ('CORRUPCION','FRAUDE_CONTRACTUAL')},
              'random_expected_recall': {'0.01': .01, '0.05': .05, '0.1': .1},
              'case_interval': interval, 'unseen_suppliers': unseen_interval, 'slices': slices,
              'sector_definition': 'Segmento UNSPSC (dos primeros dígitos de código de ocho dígitos); no es sector institucional.',
              'sector_reference': 'https://colombiacompra.gov.co/sites/cce_public/files/cce_clasificador/manualclasificador.pdf',
              'baseline_complete_for_comparison': baseline_complete,
              'validated': baseline_complete and interval['passed'] and unseen_interval['passed'],
              'limitations': ['Etiquetas judiciales seleccionadas, no muestra aleatoria de toda la corrupción.',
                             'No se estiman precisión real, falsos positivos ni probabilidad de corrupción.',
                             'Bootstrap por expediente condicionado al ranking del conjunto de reserva.',
                             'El ranking de reglas incompletas usa un límite inferior descriptivo; no acredita mejora validada.']}
    report['sha256'] = digest(report)
    return artifact, report
