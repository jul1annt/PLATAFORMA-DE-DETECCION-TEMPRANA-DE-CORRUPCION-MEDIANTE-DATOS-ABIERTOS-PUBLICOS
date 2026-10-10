import pytest

from core.config import normalize_cors_origins


def test_cors_origins_are_normalized_and_deduplicated():
    assert normalize_cors_origins([
        " https://Example.COM:443/ ",
        "http://localhost:5173",
        "https://example.com",
        "http://[::1]:5173",
    ]) == [
        "https://example.com",
        "http://localhost:5173",
        "http://[::1]:5173",
    ]


@pytest.mark.parametrize(
    "origins",
    [
        [],
        ["*"],
        ["null"],
        ["ftp://example.com"],
        ["https://user@example.com"],
        ["https://example.com/app"],
        ["https://example.com?debug=true"],
        ["https://example.com:invalid"],
    ],
)
def test_cors_rejects_wildcard_or_non_origin_values(origins):
    with pytest.raises(ValueError):
        normalize_cors_origins(origins)


def test_application_cors_allows_configured_bearer_and_export_headers_only():
    from fastapi.testclient import TestClient

    from core.config import settings
    from main import app

    client = TestClient(app)
    origin = settings.CORS_ORIGINS[0]
    allowed = client.options(
        "/api/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,x-export-token",
        },
    )
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in allowed.headers

    denied_origin = client.options(
        "/api/auth/me",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert denied_origin.status_code == 400
    assert "access-control-allow-origin" not in denied_origin.headers

    denied_header = client.options(
        "/api/auth/me",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "x-unapproved-header",
        },
    )
    assert denied_header.status_code == 400
