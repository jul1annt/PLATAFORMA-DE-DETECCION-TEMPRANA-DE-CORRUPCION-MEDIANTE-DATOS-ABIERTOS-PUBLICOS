"""Loopback-only API for the isolated citizen risk snapshot."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SQLITE_SNAPSHOT = ROOT / ".codex-analytics-postgres" / "mvp-risk-20261020" / "full-volume-v3.sqlite"
JSON_SNAPSHOT = ROOT / ".codex-analytics-postgres" / "mvp-risk-20261020" / "snapshot-v8.json"
SNAPSHOT_DATA = None
KEEPALIVE = None


def open_snapshot():
    if SQLITE_SNAPSHOT.is_file():
        return sqlite3.connect(f"file:{SQLITE_SNAPSHOT.as_posix()}?mode=ro", uri=True, timeout=20)
    return None


def row_to_api(row):
    (contract_id, raw_id, process_id, entity, supplier, published, contract_type,
     modality, amount, award_amount, stage, period, source_url, signal, status,
     evidence, coverage, missing, legacy) = row
    return {
        "id": contract_id,
        "raw_secop_id": raw_id,
        "process_id": process_id,
        "entity": entity,
        "supplier": supplier,
        "published_at": published,
        "contract_type": contract_type,
        "modality": modality,
        "amount": amount,
        "award_amount": award_amount,
        "stage": stage,
        "comparison_period": period,
        "source_url": source_url,
        "signal": signal == 1 if signal is not None else False,
        "status": status,
        "coverage": json.loads(coverage),
        "missing_evidence": json.loads(missing),
        "evidence": json.loads(evidence),
        "legacy_data_quality_flag": bool(legacy),
        "priority": {"priority_is_fully_resolved": False, "review_route": "UNRANKED_STATISTICAL_REVIEW"},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "IndiciosMVP/3.0"

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:4174")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.headers.get("Origin") not in (None, "http://127.0.0.1:4174"):
            self.send_error(403)
            return
        parsed = urlparse(self.path)
        if SQLITE_SNAPSHOT.is_file():
            self._get_sqlite(parsed)
            return
        data = SNAPSHOT_DATA
        if data is None:
            self._send(503, {"error": "El corte local no está disponible."})
            return
        if parsed.path == "/api/indicios/estado":
            state = {k: data[k] for k in ("name", "status", "snapshot_cut", "cohort", "created_at", "coverage",
                                          "index", "priority_analysis", "source_hash_sha256",
                                          "database_generation_consistency_verified", "cohort_generation_note")}
            state["filters"] = {
                "contract_types": sorted({r["contract_type"] for r in data["results"] if r.get("contract_type")}),
                "modalities": sorted({r["modality"] for r in data["results"] if r.get("modality")}),
                "stages": sorted({r["stage"] for r in data["results"]}),
            }
            self._send(200, state)
        elif parsed.path == "/api/indicios/metodologia":
            self._send(200, {"methodology": data["methodology"], "status": data["status"], "index": data["index"]})
        elif parsed.path == "/api/indicios/contrato":
            raw_id = parse_qs(parsed.query).get("raw_id", [""])[0]
            row = next((r for r in data["results"] if str(r.get("raw_secop_id")) == raw_id), None)
            self._send(200 if row else 404, row or {"error": "No hay evaluación disponible para este contrato."})
        elif parsed.path == "/api/indicios/resultados":
            self._get_json_results(data, parse_qs(parsed.query))
        else:
            self.send_error(404)

    def _get_sqlite(self, parsed):
        path = parsed.path
        conn = open_snapshot()
        try:
            if path == "/api/indicios/estado":
                state = {key: json.loads(value) for key, value in conn.execute(
                    "SELECT key,value FROM meta WHERE key NOT IN ('filters','artifact')")}
                state["filters"] = json.loads(conn.execute("SELECT value FROM meta WHERE key='filters'").fetchone()[0])
                self._send(200, state)
            elif path == "/api/indicios/metodologia":
                state = {key: json.loads(value) for key, value in conn.execute(
                    "SELECT key,value FROM meta WHERE key IN ('methodology','status','index')")}
                self._send(200, state)
            elif path == "/api/indicios/contrato":
                raw_id = parse_qs(parsed.query).get("raw_id", [""])[0]
                if not raw_id.isdigit():
                    self._send(400, {"error": "Identificador SECOP inválido."})
                    return
                row = conn.execute("SELECT * FROM results WHERE raw_secop_id=?", (int(raw_id),)).fetchone()
                self._send(200 if row else 404, row_to_api(row) if row else {"error": "No hay evaluación disponible para este contrato."})
            elif path == "/api/indicios/resultados":
                self._get_sqlite_results(conn, parse_qs(parsed.query))
            else:
                self.send_error(404)
        except sqlite3.Error:
            self._send(503, {"error": "El índice local de indicios no está disponible."})
        finally:
            if conn is not None:
                conn.close()

    def _get_sqlite_results(self, conn, query):
        try:
            page = max(1, min(400_000, int(query.get("page", ["1"])[0])))
            size = max(1, min(100, int(query.get("size", ["25"])[0])))
        except ValueError:
            self._send(400, {"error": "Paginación inválida."})
            return

        where = []
        params = {}
        for key, column in (("contract_type", "contract_type"), ("modality", "modality")):
            value = query.get(key, [""])[0].strip()
            if value:
                where.append(f"r.{column} = :{key}")
                params[key] = value
        for key, values in (("status", {"CON_SENAL_CONFIRMADA", "EVIDENCIA_INSUFICIENTE", "NO_EVALUABLE", "SIN_SENAL_OBSERVADA"}),
                            ("stage", {"CONVOCATORIA", "ADJUDICACION"})):
            value = query.get(key, [""])[0]
            if value in values:
                where.append(f"r.{key} = :{key}")
                params[key] = value
        signal = query.get("signal", [""])[0]
        signal_filter = int(signal == "true") if signal in ("true", "false") else None
        if signal_filter == 1:
            where.append("r.signal = 1")
        elif signal_filter == 0:
            where.append("(r.signal = 0 OR r.signal IS NULL)")
        term = query.get("q", [""])[0].strip()[:100]
        join_fts = ""
        if term:
            if len(term) < 3:
                self._send(400, {"error": "Escribe al menos tres caracteres para buscar."})
                return
            has_fts = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='results_fts'").fetchone()
            if has_fts:
                join_fts = "JOIN results_fts f ON f.rowid=r.id"
                where.append("results_fts MATCH :term")
                params["term"] = '"' + term.replace('"', '""') + '"'
            else:
                where.append("(r.process_id = :term OR CAST(r.raw_secop_id AS TEXT) = :term OR r.process_id LIKE :like_term OR r.entity LIKE :like_term OR r.supplier LIKE :like_term)")
                params["term"] = term
                params["like_term"] = "%" + term.replace("%", "\\%").replace("_", "\\_") + "%"
        where_sql = " WHERE " + " AND ".join(where) if where else ""
        offset = (page - 1) * size
        page_limit = page * size + 1
        rows = []
        partitioned = False
        status_values = ("CON_SENAL_CONFIRMADA", "EVIDENCIA_INSUFICIENTE", "NO_EVALUABLE", "SIN_SENAL_OBSERVADA")
        stage_values = ("CONVOCATORIA", "ADJUDICACION")
        has_type_modality_index = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='index' AND name='ix_results_type_modality'"
        ).fetchone() is not None

        if "status" in params or "stage" in params:
            partitioned = True
            base_where = [clause for clause in where if clause not in ("r.status = :status", "r.stage = :stage", "r.signal = 1", "(r.signal = 0 OR r.signal IS NULL)")]
            base_params = {key: value for key, value in params.items() if key not in ("status", "stage", "signal")}
            statuses = [params["status"]] if "status" in params else status_values
            stages = [params["stage"]] if "stage" in params else stage_values
            for status_value in statuses:
                for stage_value in stages:
                    expected_signal = 1 if status_value == "CON_SENAL_CONFIRMADA" else 0
                    if signal_filter is not None and signal_filter != expected_signal:
                        continue
                    signal_clause = "r.signal = 1" if expected_signal else "(r.signal = 0 OR r.signal IS NULL)"
                    clauses = [*base_where, "r.status = :status", "r.stage = :stage", signal_clause]
                    partition = conn.execute(
                        f"SELECT r.* FROM results r INDEXED BY ix_results_status_stage {join_fts} WHERE {' AND '.join(clauses)} "
                        "ORDER BY r.published_at DESC, r.raw_secop_id ASC LIMIT :limit",
                        {**base_params, "status": status_value, "stage": stage_value, "limit": page_limit},
                    ).fetchall()
                    rows.extend(partition)
        elif signal_filter == 0 and not term and "contract_type" not in params and "modality" not in params:
            partitioned = True
            base_where = [clause for clause in where if clause != "(r.signal = 0 OR r.signal IS NULL)"]
            base_params = {key: value for key, value in params.items() if key != "signal"}
            for signal_clause in ("r.signal = 0", "r.signal IS NULL"):
                clauses = [*base_where, signal_clause]
                partition = conn.execute(
                    f"SELECT r.* FROM results r INDEXED BY ix_results_public_order {join_fts} WHERE {' AND '.join(clauses)} "
                    "ORDER BY r.signal DESC, r.published_at DESC, r.raw_secop_id LIMIT :limit",
                    {**base_params, "limit": page_limit},
                ).fetchall()
                rows.extend(partition)
        elif ("contract_type" in params or "modality" in params) and has_type_modality_index:
            partitioned = True
            filter_row = conn.execute("SELECT value FROM meta WHERE key='filters'").fetchone()
            filters = json.loads(filter_row[0]) if filter_row else {}
            types = [params["contract_type"]] if "contract_type" in params else filters.get("contract_types", [])
            modalities = [params["modality"]] if "modality" in params else filters.get("modalities", [])
            base_where = [clause for clause in where if clause not in ("r.contract_type = :contract_type", "r.modality = :modality", "r.signal = 1", "(r.signal = 0 OR r.signal IS NULL)")]
            base_params = {key: value for key, value in params.items() if key not in ("contract_type", "modality", "signal")}
            signal_values = [signal_filter] if signal_filter is not None else [1, 0]
            for contract_type in types:
                for modality in modalities:
                    for signal_value in signal_values:
                        signal_clause = "r.signal = 1" if signal_value else "(r.signal = 0 OR r.signal IS NULL)"
                        clauses = [*base_where, "r.contract_type = :contract_type", "r.modality = :modality", signal_clause]
                        partition = conn.execute(
                            f"SELECT r.* FROM results r INDEXED BY ix_results_type_modality {join_fts} WHERE {' AND '.join(clauses)} "
                            "ORDER BY r.published_at DESC, r.raw_secop_id ASC LIMIT :limit",
                            {**base_params, "contract_type": contract_type, "modality": modality, "limit": page_limit},
                        ).fetchall()
                        rows.extend(partition)
        else:
            rows = conn.execute(
                f"SELECT r.* FROM results r {join_fts}{where_sql} "
                "ORDER BY r.signal DESC, r.published_at DESC, r.raw_secop_id LIMIT :limit OFFSET :offset",
                {**params, "limit": size + 1, "offset": offset},
            ).fetchall()

        if partitioned:
            rows.sort(key=lambda row: row[1])
            rows.sort(key=lambda row: row[5] or "", reverse=True)
            rows.sort(key=lambda row: bool(row[13]), reverse=True)
            rows = rows[offset:offset + size + 1]
        has_more = len(rows) > size
        rows = rows[:size]
        total = None
        if not where:
            cohort = conn.execute("SELECT value FROM meta WHERE key='cohort'").fetchone()
            if cohort:
                total = json.loads(cohort[0]).get("rows")
        self._send(200, {"total": total, "has_more": has_more, "page": page, "size": size, "items": [row_to_api(r) for r in rows]})

    def _get_json_results(self, data, query):
        rows = data["results"]
        for key in ("contract_type", "modality"):
            value = query.get(key, [""])[0].strip().casefold()
            if value:
                rows = [r for r in rows if (r.get(key) or "").casefold() == value]
        status = query.get("status", [""])[0]
        if status in ("CON_SENAL_CONFIRMADA", "EVIDENCIA_INSUFICIENTE", "NO_EVALUABLE", "SIN_SENAL_OBSERVADA"):
            rows = [r for r in rows if r["status"] == status]
        stage = query.get("stage", [""])[0]
        if stage in ("CONVOCATORIA", "ADJUDICACION"):
            rows = [r for r in rows if r["stage"] == stage]
        signal = query.get("signal", [""])[0]
        if signal in ("true", "false"):
            rows = [r for r in rows if r["signal"] is (signal == "true")]
        term = query.get("q", [""])[0].strip().casefold()[:100]
        if term:
            rows = [r for r in rows if any(term in str(r.get(k) or "").casefold() for k in ("process_id", "entity", "supplier"))]
        try:
            page = max(1, min(10_000, int(query.get("page", ["1"])[0])))
            size = max(1, min(100, int(query.get("size", ["25"])[0])))
        except ValueError:
            self._send(400, {"error": "Paginación inválida."})
            return
        start = (page - 1) * size
        items = rows[start:start + size + 1]
        self._send(200, {"total": len(rows), "has_more": len(items) > size, "page": page, "size": size, "items": items[:size]})

    def _send(self, status, value):
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if self.headers.get("Origin") == "http://127.0.0.1:4174":
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:4174")
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    if SQLITE_SNAPSHOT.is_file():
        # Keep one read-only handle open so Windows retains SQLite's WAL index
        # between requests; per-request handles can then close without forcing
        # a full 37 GB WAL-index rebuild on the next request.
        KEEPALIVE = open_snapshot()
        cursor = KEEPALIVE.execute("SELECT 1 FROM sqlite_master LIMIT 1")
        cursor.fetchone()
        cursor.close()
    elif JSON_SNAPSHOT.is_file():
        SNAPSHOT_DATA = json.loads(JSON_SNAPSHOT.read_text(encoding="utf-8"))
    else:
        raise SystemExit("Falta generar el corte local del MVP")
    port = int(os.environ.get("MVP_INDICIOS_PORT", "8011"))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
