"""Filesystem artifacts and short-lived capability tokens for generated exports."""

import hashlib
import hmac
import os
import time
import uuid
from pathlib import Path

from core.config import settings


EXPORT_FORMATS = {"csv", "xlsx", "pdf"}


def _artifact_root(directory: str | Path | None = None) -> Path:
    return Path(directory or settings.EXPORT_ARTIFACT_DIR).expanduser().resolve()


def artifact_path(
    job_id: uuid.UUID,
    fmt: str,
    *,
    directory: str | Path | None = None,
) -> Path:
    if fmt not in EXPORT_FORMATS:
        raise ValueError("Formato de exportación inválido")
    return _artifact_root(directory) / f"{job_id}.{fmt}"


def write_artifact(
    job_id: uuid.UUID,
    fmt: str,
    content: bytes,
    *,
    directory: str | Path | None = None,
) -> tuple[Path, str]:
    target = artifact_path(job_id, fmt, directory=directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{job_id}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target, hashlib.sha256(content).hexdigest()


def result_artifact_path(job_id: uuid.UUID, result: dict, *,
                         directory: str | Path | None = None) -> Path:
    """Resolve only a validated server identifier, with legacy filename support."""
    artifact_id = job_id
    if "artifact_id" in result:
        try:
            artifact_id = uuid.UUID(str(result["artifact_id"]))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Identificador de archivo de exportación inválido") from exc
    return artifact_path(artifact_id, result.get("format"), directory=directory)


def create_export_token(job_id: uuid.UUID, expires_at: int) -> str:
    message = f"{job_id}.{expires_at}".encode("ascii")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{expires_at}.{signature}"


def parse_export_token(job_id: uuid.UUID, token: str | None) -> int | None:
    if not token:
        return None
    try:
        expires_text, provided_signature = token.split(".", 1)
        expires_at = int(expires_text)
    except (ValueError, AttributeError):
        return None
    message = f"{job_id}.{expires_at}".encode("ascii")
    expected_signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(provided_signature, expected_signature):
        return None
    return expires_at


def cleanup_expired_artifacts(
    *,
    now: float | None = None,
    directory: str | Path | None = None,
) -> int:
    root = _artifact_root(directory)
    if not root.exists():
        return 0
    current_time = time.time() if now is None else now
    max_age = settings.EXPORT_ARTIFACT_TTL_HOURS * 60 * 60
    removed = 0
    for candidate in root.iterdir():
        if not candidate.is_file() or candidate.suffix.lower() not in {".csv", ".xlsx", ".pdf", ".tmp"}:
            continue
        try:
            if current_time - candidate.stat().st_mtime >= max_age:
                candidate.unlink()
                removed += 1
        except FileNotFoundError:
            continue
    return removed
