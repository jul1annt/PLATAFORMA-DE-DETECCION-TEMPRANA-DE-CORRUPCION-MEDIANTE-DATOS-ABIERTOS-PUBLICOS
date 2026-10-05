"""Verify retained scale-trial evidence offline, using only the Python stdlib."""
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path


def quantiles(values):
    values = sorted(values)
    return {'count': len(values), 'minimum': values[0],
            'median': statistics.median(values),
            'p95_nearest_rank': values[math.ceil(.95 * len(values)) - 1],
            'maximum': values[-1]}


def verify():
    root = Path(__file__).resolve().parents[2]
    report = json.loads(Path(__file__).with_name(
        'RECUPERACION_ESCRITURAS_ESCALA_20261005.json').read_text(encoding='utf-8'))
    assert report['stage'] == 'verified_and_cleaned'
    assert report['baseline'] == report['retained_source_after']
    assert report['cleanup']['temporary_database_removed']
    assert report['post_trial_independent_audit']['operational_readonly_counts'] == {
        'raw_secop': 18980, 'contratos_procesados': 18980}
    streams = {}
    for item in report['published_artifacts']:
        path = (root / item['path']).resolve()
        assert path.is_relative_to(root / 'docs/auditoria')
        assert path.stat().st_size == item['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        if path.name.endswith('.jsonl.gz'):
            with gzip.open(path, 'rt', encoding='utf-8') as source:
                streams[path.name] = [json.loads(line) for line in source]
    events = streams['worker_scale_20261005_recovered_batches.jsonl.gz']
    assert events[0]['kind'] == 'anchor' and events[0]['rows'] == 26000
    cursor = 26000
    for event in events[1:]:
        assert event['kind'] == 'batch' and event['delta_rows'] > 0
        assert event['rows'] == cursor + event['delta_rows'] == event['last_raw_id']
        cursor = event['rows']
    assert cursor == report['expected_raw_rows'] == 9249545
    assert len(events) - 1 == report['resumed_batch_count']
    assert quantiles([event['batch_seconds'] for event in events[1:]]) == report['resumed_batch_seconds']
    job = report['completed_job']
    assert job['status'] == 'EXITOSO' and job['active'] is False and job['attempts'] == 2
    assert job['result']['total_evaluados'] == cursor
    assert job['result']['procesados'] + job['result']['omitidos'] == cursor
    assert report['final_counts']['raw_secop'] == report['final_counts']['contratos_procesados'] == cursor
    assert report['final_counts']['contrato_anomalo_incompleto'] == job['result']['anomalias_registradas']
    assert [(log['estado'], log['total_evaluados']) for log in report['processing_logs']] == [('ERROR', 26000), ('EXITOSO', cursor)]
    requests = streams['worker_scale_20261005_resumed_http.jsonl.gz']
    assert all(item['status_code'] == 200 for item in requests)
    for kind in ('status', 'search_2024'):
        items = [item for item in requests if item['route_kind'] == kind]
        assert quantiles([item['milliseconds'] for item in items]) == report['http_summaries'][kind]
        if kind == 'search_2024':
            assert all(item['total'] == 1670370 and item['items'] == 20 for item in items)
    resources = streams['worker_scale_20261005_resumed_resources.jsonl.gz'] + streams['worker_scale_20261005_pilot_resources_salvaged.jsonl.gz']
    summary = report['resource_sampling']
    assert len(resources) == summary['samples']
    for field, sample_key in (('maximum_owned_private_bytes_sum', 'owned_private_bytes_sum'),
                              ('maximum_owned_working_set_bytes_sum', 'owned_working_set_bytes_sum')):
        assert max(item[sample_key] for item in resources) == summary[field]
    assert min(item['free_disk_bytes'] for item in resources) == summary['minimum_free_disk_bytes']
    print(json.dumps({'verified': True, 'evaluated_rows': cursor,
                      'resumed_batches': len(events) - 1,
                      'http_200': len(requests), 'resource_samples': len(resources)}))


if __name__ == '__main__':
    verify()
