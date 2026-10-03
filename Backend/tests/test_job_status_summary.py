from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from core.database import get_db
from gateway.middlewares.auth_middleware import get_current_admin
from main import app
from modules.jobs.service import get_job_status_summary


def test_job_status_summary_groups_all_jobs_in_one_sql_statement():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE background_jobs (id INTEGER PRIMARY KEY, status VARCHAR(20) NOT NULL)"
        ))
        connection.execute(text("""
            INSERT INTO background_jobs (id, status)
            VALUES (1, 'PENDIENTE'), (2, 'EN_PROCESO'), (3, 'EXITOSO'), (4, 'ERROR'),
                   (5, 'EXITOSO'), (6, 'PARCIAL')
        """))

    statements = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _parameters, _context, _many: statements.append(statement),
    )
    try:
        with Session(engine) as session:
            summary = get_job_status_summary(session)
        selects = [statement for statement in statements if statement.lstrip().upper().startswith("SELECT")]
    finally:
        engine.dispose()

    assert summary.total == 6
    assert summary.by_status == {
        "PENDIENTE": 1,
        "EN_PROCESO": 1,
        "PARCIAL": 1,
        "EXITOSO": 2,
        "ERROR": 1,
    }
    assert len(selects) == 1


def test_job_status_summary_rejects_anonymous_and_unknown_query_params():
    client = TestClient(app)
    anonymous = client.get("/api/jobs/resumen")
    assert anonymous.status_code == 401

    app.dependency_overrides[get_current_admin] = lambda: object()
    app.dependency_overrides[get_db] = lambda: object()
    try:
        response = client.get("/api/jobs/resumen?unexpected=true")
    finally:
        app.dependency_overrides.pop(get_current_admin, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422
