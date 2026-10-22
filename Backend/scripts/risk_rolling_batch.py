"""Serial, resumable offline diagnostics bound to frozen inputs and code hashes."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import platform
from pathlib import Path, PureWindowsPath
import re
import sys
import uuid

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from modules.motor_riesgo.rolling_evidence import assess, POLICY
from modules.motor_riesgo.baseline_coverage import baseline_coverage

MAX_FILE = 16 * 1024 * 1024
MAX_BATCH = 256 * 1024 * 1024


def read(path, maximum=MAX_FILE):
    with path.open('rb') as stream:
        body = stream.read(maximum + 1)
    if len(body) > maximum:
        raise ValueError('Entrada demasiado grande')
    return body


def sha(body):
    return hashlib.sha256(body).hexdigest()


def code_hashes():
    paths = [Path(__file__), BACKEND / 'modules/__init__.py',
             *(BACKEND / 'modules/motor_riesgo' / name for name in
              ('__init__.py', 'rolling_evidence.py', 'cut_rules.py', 'rules.py', 'baseline_coverage.py', 'weight_lab.py', 'domain.py'))]
    return {str(path.relative_to(BACKEND)).replace('\\', '/'): sha(path.read_bytes()) for path in paths}


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()


def persist(path, value):
    """Under the batch lock, recover only identical complete artifacts."""
    return persist_bytes(path, encode(value))


def persist_bytes(path, body):
    if path.exists():
        if path.is_symlink() or path.read_bytes() != body:
            raise ValueError('Artefacto existente incompatible o alterado')
        return True
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.partial')
    try:
        with temporary.open('xb') as stream:
            stream.write(body); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()
    return False


@contextmanager
def batch_lock(path):
    """OS-owned nonblocking lock: process termination releases ownership."""
    if path.is_symlink():
        raise ValueError('Bloqueo no puede ser enlace simbólico')
    with path.open('a+b') as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def run(manifest_path, output):
    manifest_path = manifest_path.resolve()
    body = read(manifest_path, 1024 * 1024)
    manifest = json.loads(body)
    entries = manifest['inputs']
    if (manifest.get('version') != 'rolling-batch-input-v1' or not isinstance(entries, list)
            or not 1 <= len(entries) <= 1000):
        raise ValueError('Manifiesto de lote inválido')
    inputs, seen, total = [], set(), 0
    for entry in entries:
        input_name = entry['path']
        relative = Path(input_name)
        windows_relative = PureWindowsPath(input_name)
        if (relative.is_absolute() or relative.drive or '..' in relative.parts
                or windows_relative.is_absolute() or windows_relative.drive
                or '..' in windows_relative.parts):
            raise ValueError('Ruta debe ser relativa al manifiesto')
        path = (manifest_path.parent / relative).resolve()
        if not path.is_relative_to(manifest_path.parent) or path in seen:
            raise ValueError('Ruta repetida o fuera del marco')
        seen.add(path)
        expected = entry['sha256']
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('Hash inválido')
        raw = read(path); total += len(raw)
        if total > MAX_BATCH or sha(raw) != expected:
            raise ValueError('Límite del lote o hash de entrada incompatible')
        inputs.append((path, expected))
    hashes = code_hashes()
    binding = {'version': 'rolling-offline-batch-v1', 'input_manifest_sha256': sha(body),
               'implementation_sha256': hashes, 'rolling_policy': POLICY, 'concurrency': 1,
               'python_version': platform.python_version(), 'python_implementation': platform.python_implementation(),
               'training_eligible': False, 'publication_authorized': False}
    output = output.resolve(); output.mkdir(parents=True, exist_ok=True)
    records, resumed = [], 0
    with batch_lock(output / '.lock'):
        persist(output / 'binding.json', binding)
        for relative, expected in hashes.items():
            code = (BACKEND / relative).read_bytes()
            if sha(code) != expected:
                raise ValueError('El código cambió antes de congelarlo')
            target = output / 'code' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            persist_bytes(target, code)
        for index, (path, expected) in enumerate(inputs):
            raw = read(path)
            if sha(raw) != expected:
                raise ValueError('La entrada cambió durante el lote')
            report = assess(json.loads(raw))
            report['coverage'] = baseline_coverage(report['values'], 'ADJUDICACION')
            report['input_sha256'] = expected
            report['implementation_sha256'] = hashes
            name = f'result-{index:06d}.json'
            resumed += persist(output / name, report)
            records.append({'path': name, 'sha256': sha(encode(report)), 'input_sha256': expected,
                            'complete_risk_score': report['coverage']['complete_score']})
        # An interrupted batch has no complete receipt. Recheck inputs before
        # writing it, even when an earlier report was safely reused.
        if code_hashes() != hashes or sha(read(manifest_path, 1024 * 1024)) != sha(body):
            raise ValueError('El código o manifiesto cambió durante el lote')
        for path, expected in inputs:
            if sha(read(path)) != expected:
                raise ValueError('La entrada cambió durante el lote')
        complete = {**binding, 'status': 'COMPLETE_OFFLINE_DIAGNOSTIC', 'results': records,
                    'complete_risk_scores': sum(row['complete_risk_score'] is not None for row in records)}
        persist(output / 'complete.json', complete)
    return {'results': len(records), 'reused_identical_results': resumed,
            'complete_risk_scores': complete['complete_risk_scores'], 'publication_authorized': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.output_directory)))


if __name__ == '__main__':
    main()
