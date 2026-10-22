"""Deterministic JSONL compression, with no training or API dependency."""
from contextlib import contextmanager
import gzip
import hashlib
from pathlib import Path


@contextmanager
def binary_stream(path: Path, mode: str):
    with path.open(mode) as raw:
        if path.name.endswith('.gz'):
            with gzip.GzipFile(filename='', mode='rb' if 'r' in mode else 'wb', fileobj=raw,
                               **({} if 'r' in mode else {'compresslevel': 1, 'mtime': 0})) as stream:
                yield stream
        else:
            yield raw


def logical_sha256(path: Path, maximum_bytes: int | None = None) -> str:
    checksum = hashlib.sha256()
    size = 0
    with binary_stream(path, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            size += len(block)
            if maximum_bytes is not None and size > maximum_bytes:
                raise ValueError('El conjunto supera el límite descomprimido')
            checksum.update(block)
    return checksum.hexdigest()


def physical_sha256(path: Path) -> str:
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()
