from fastapi.testclient import TestClient

from app.api import rate_limit
from tests.helpers import lead_form, resume_file


def test_healthz(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_openapi_lists_the_lead_endpoints(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/api/v1/leads", "/api/v1/leads/{lead_id}", "/api/v1/leads/{lead_id}/resume"} <= set(
        paths
    )


def test_unknown_route_uses_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_public_form_is_rate_limited(client: TestClient, settings, monkeypatch) -> None:
    limited = settings.model_copy(update={"rate_limit_create_lead": "2/minute"})
    monkeypatch.setattr(rate_limit, "get_settings", lambda: limited)
    rate_limit.limiter.enabled = True
    rate_limit.limiter.reset()
    try:
        codes = [
            client.post("/api/v1/leads", data=lead_form(), files=resume_file()).status_code
            for _ in range(3)
        ]
    finally:
        rate_limit.limiter.enabled = False
        rate_limit.limiter.reset()

    assert codes == [201, 201, 429]
