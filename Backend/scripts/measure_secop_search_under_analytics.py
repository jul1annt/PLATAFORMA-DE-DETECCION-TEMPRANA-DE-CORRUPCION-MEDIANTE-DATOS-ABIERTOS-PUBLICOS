"""Measure a bounded real search endpoint while full-universe analytics run."""

import json
import math
import os
import shutil
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / ".codex-e2e-postgres"
TARGET = "plataforma_secop_refresh_20261001_test"
OUTPUT = ARTIFACTS / "search_api_during_20261001_analytics.json"
PIPELINE = ARTIFACTS / "secop_20261001_pipeline_manifest.json"
ROUTE = (
    "/api/procesados/search?fecha_inicio=2024-01-01"
    "&fecha_fin=2024-12-31&limit=20&sort=fecha&order=desc"
)
REQUESTS = 8
WORKERS = 2

load_dotenv(ROOT / ".env")
os.environ.update(DB_HOST="127.0.0.1", DB_PORT="5433", DB_NAME=TARGET)
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from core.database import engine  # noqa: E402
from main import app  # noqa: E402


def sample():
    with TestClient(app) as client:
        start = time.perf_counter()
        response = client.get(ROUTE)
        elapsed_ms = (time.perf_counter() - start) * 1000
        body = response.json() if response.status_code == 200 else None
        return {
            "status": response.status_code,
            "milliseconds": round(elapsed_ms, 2),
            "total": body.get("total") if isinstance(body, dict) else None,
            "items": len(body.get("items", [])) if isinstance(body, dict) else None,
        }


def main():
    if OUTPUT.exists():
        raise RuntimeError("Previous report exists; refusing to overwrite it")
    with engine.connect() as db:
        identity = db.execute(text(
            "SELECT current_database(), current_setting('data_directory')"
        )).one()
        if identity[0] != TARGET or "recovery-clone-20260929" not in identity[1]:
            raise RuntimeError("Benchmark target is not the isolated SECOP generation")
    before = json.loads(PIPELINE.read_text(encoding="utf-8"))
    if before.get("stage") != "running_analytics":
        raise RuntimeError("Full-universe analytics are not running")
    disk_before = shutil.disk_usage(ARTIFACTS.anchor).free
    warmup = sample()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(lambda _: sample(), range(REQUESTS)))
    after = json.loads(PIPELINE.read_text(encoding="utf-8"))
    latencies = sorted(item["milliseconds"] for item in results)
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "database": TARGET,
        "route": ROUTE,
        "method": "FastAPI TestClient, real isolated PostgreSQL and live analytics",
        "analytics_stage_before": before.get("stage"),
        "analytics_stage_after": after.get("stage"),
        "concurrent_clients": WORKERS,
        "requests": REQUESTS,
        "warmup": warmup,
        "statuses": {
            str(code): sum(item["status"] == code for item in results)
            for code in sorted({item["status"] for item in results})
        },
        "totals": sorted({item["total"] for item in results if item["total"] is not None}),
        "items": sorted({item["items"] for item in results if item["items"] is not None}),
        "latency_ms": {
            "min": latencies[0],
            "median": round(statistics.median(latencies), 2),
            "p95_nearest_rank": latencies[math.ceil(0.95 * len(latencies)) - 1],
            "max": latencies[-1],
        },
        "disk_free_gib_before": round(disk_before / 2**30, 2),
        "disk_free_gib_after": round(shutil.disk_usage(ARTIFACTS.anchor).free / 2**30, 2),
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if report["statuses"] != {"200": REQUESTS}:
        raise RuntimeError("Search API returned an unexpected status")


if __name__ == "__main__":
    main()
