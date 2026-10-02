"""PostgreSQL integration coverage for the main administrator workflow."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.database import get_db
from main import app
from modules.auth.model.Admin import Admin
from modules.auth.model.AdminSession import AdminSession
from modules.auth.service.AuthService import AuthService
from modules.ingesta.model.RawSecopHistorial import RawSecopHistorial
from modules.jobs.model import BackgroundJob
from modules.jobs import worker as job_worker


def test_admin_can_ingest_transform_analyze_search_and_export(
    postgres_test_session, monkeypatch
):
    connection = postgres_test_session.connection()
    monkeypatch.setattr(
        job_worker,
        "SessionLocal",
        lambda: Session(bind=connection, join_transaction_mode="create_savepoint"),
    )

    suffix = uuid.uuid4().hex
    admin = Admin(
        username=f"workflow-{suffix[:16]}",
        email=f"workflow-{suffix}@example.test",
        hashed_password=AuthService(postgres_test_session).hash_password("workflow-password-123"),
        is_active=True,
    )
    postgres_test_session.add(admin)
    postgres_test_session.flush()

    base_date = date.today() - timedelta(days=5)
    records = []
    for index, value in enumerate((10000, 11000, 12000, 13000, 50000000)):
        published = base_date + timedelta(days=index)
        records.append({
            ":id": f"workflow-{suffix}-{index}",
            ":updated_at": datetime.now(timezone.utc).isoformat(),
            "id_del_proceso": f"workflow-process-{suffix}-{index}",
            "entidad": "Entidad flujo de prueba",
            "nit_entidad": "900123456",
            "nombre_del_proveedor": "Proveedor flujo de prueba",
            "nit_del_proveedor_adjudicado": "800765432",
            "fecha_de_publicacion_del": published.isoformat(),
            "fecha_adjudicacion": published.isoformat(),
            "valor_total_adjudicacion": str(value),
            "precio_base": str(value),
            "tipo_de_contrato": "Servicios",
            "modalidad_de_contratacion": "CONTRATACIÓN DIRECTA",
            "estado_del_procedimiento": "Adjudicado",
            "ciudad_entidad": "Bogotá",
            "departamento_entidad": "Bogotá D.C.",
            "urlproceso": f"https://www.datos.gov.co/resource/p6dx-8zbt.json?test={index}",
        })

    class FakeAdapter:
        def fetch_todos(self, **_kwargs):
            yield records

    monkeypatch.setattr(
        "modules.ingesta.services.IngestaService.get_adapter",
        lambda *_args, **_kwargs: FakeAdapter(),
    )

    def override_get_db():
        yield postgres_test_session

    app.dependency_overrides[get_db] = override_get_db
    public_job_ids: list[str] = []
    try:
        with TestClient(app) as client:
            login = client.post(
                "/api/auth/login",
                json={"username": admin.username, "password": "workflow-password-123"},
            )
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            source_response = client.post(
                "/api/ingesta/fuentes/",
                headers=headers,
                json={
                    "nombre": f"SECOP flujo {suffix[:12]}",
                    "tipo": "SECOP",
                    "formato": "JSON",
                    "endpoint": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
                },
            )
            assert source_response.status_code == 201
            source_id = source_response.json()["id"]

            updated_source = client.put(
                f"/api/ingesta/fuentes/{source_id}",
                headers=headers,
                json={"frecuencia_dias": 7},
            )
            assert updated_source.status_code == 200
            assert updated_source.json()["frecuencia_dias"] == 7

            ingestion = client.post(
                f"/api/ingesta/fuentes/{source_id}/sincronizar", headers=headers
            )
            assert ingestion.status_code == 202
            public_job_ids.append(ingestion.json()["id"])
            assert job_worker.process_next_job() is True
            ingestion_status = client.get(
                ingestion.json()["status_url"], headers=headers
            )
            assert ingestion_status.json()["status"] == "EXITOSO"
            assert ingestion_status.json()["result"]["registros_insertados"] == 5

            reprocesamiento = client.post(
                "/api/procesados/reprocesar", headers=headers, json={}
            )
            assert reprocesamiento.status_code == 202
            public_job_ids.append(reprocesamiento.json()["id"])
            assert job_worker.process_next_job() is True
            assert client.get(
                reprocesamiento.json()["status_url"], headers=headers
            ).json()["status"] == "EXITOSO"

            records[0] = {
                **records[0],
                ":updated_at": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
                "valor_total_adjudicacion": "10500",
                "precio_base": "10500",
            }
            second_ingestion = client.post(
                f"/api/ingesta/fuentes/{source_id}/sincronizar", headers=headers
            )
            assert second_ingestion.status_code == 202
            public_job_ids.append(second_ingestion.json()["id"])
            assert job_worker.process_next_job() is True
            second_ingestion_status = client.get(
                second_ingestion.json()["status_url"], headers=headers
            )
            assert second_ingestion_status.json()["status"] == "EXITOSO"
            assert second_ingestion_status.json()["result"]["registros_insertados"] == 0

            history = postgres_test_session.query(RawSecopHistorial).filter_by(
                id_del_proceso=f"workflow-process-{suffix}-0"
            ).one()
            assert float(history.datos_anteriores["valor_total_adjudicacion"]) == 10000

            updated_reprocessing = client.post(
                "/api/procesados/reprocesar",
                headers=headers,
                json={"forzar_reproceso": True},
            )
            assert updated_reprocessing.status_code == 202
            public_job_ids.append(updated_reprocessing.json()["id"])
            assert job_worker.process_next_job() is True
            updated_status = client.get(
                updated_reprocessing.json()["status_url"], headers=headers
            )
            assert updated_status.json()["status"] == "EXITOSO"

            search = client.get(
                "/api/procesados/search",
                params={"proveedor": "flujo de prueba", "limit": 2},
            )
            assert search.status_code == 200
            assert search.json()["total"] == 5
            assert len(search.json()["items"]) == 2
            updated_contract = client.get(
                "/api/procesados/search",
                params={"q": f"workflow-process-{suffix}-0", "limit": 1},
            )
            assert updated_contract.json()["total"] == 1
            assert float(updated_contract.json()["items"][0]["valor_total_normalizado"]) == 10500

            dashboard = client.get("/api/procesados/metricas/dashboard")
            assert dashboard.status_code == 200
            assert dashboard.json()["total_contratos"] == 5

            analyses = (
                ("/api/analitica/outliers/calcular", {
                    "fecha_campo": "fecha_publicacion_normalizada",
                }),
                ("/api/analitica/duplicados/calcular", {}),
                ("/api/analitica/directas/calcular", {"minimo_directas": 3}),
                ("/api/analitica/riesgo/calcular", {}),
            )
            for path, payload in analyses:
                accepted = client.post(path, headers=headers, json=payload)
                assert accepted.status_code == 202
                public_job_ids.append(accepted.json()["id"])
                assert job_worker.process_next_job() is True
                status_response = client.get(
                    accepted.json()["status_url"], headers=headers
                )
                assert status_response.json()["status"] == "EXITOSO", status_response.json()

            risks = client.get("/api/analitica/riesgo", headers=headers)
            assert risks.status_code == 200
            assert risks.json()["total"] == 1

            export = client.get(
                "/api/procesados/export/csv", params={"proveedor": "flujo de prueba"}
            )
            assert export.status_code == 200
            assert "PROVEEDOR FLUJO DE PRUEBA" in export.text.upper()
            assert export.text.upper().count("PROVEEDOR FLUJO DE PRUEBA") == 5

            logout = client.post("/api/auth/logout", headers=headers)
            assert logout.status_code == 200
            assert client.get("/api/auth/me", headers=headers).status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)
        for public_id in public_job_ids:
            job = postgres_test_session.query(BackgroundJob).filter_by(
                public_id=public_id
            ).first()
            if job is not None:
                postgres_test_session.delete(job)
        postgres_test_session.query(AdminSession).filter_by(admin_id=admin.id).delete()
        postgres_test_session.delete(admin)
        postgres_test_session.flush()
