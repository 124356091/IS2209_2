from unittest.mock import patch


def test_health_endpoint_reports_dependencies(client):
    with patch("app.db.check_health", return_value=(True, "connected")), \
         patch("app.pokeapi_service.check_health", return_value=(True, "reachable")):
        resp = client.get("/health")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["status"] == "healthy"
        assert data["dependencies"]["database"]["ok"] is True
        assert data["dependencies"]["pokeapi"]["ok"] is True


def test_health_degraded_when_db_down(client):
    with patch("app.db.check_health", return_value=(False, "connection refused")), \
         patch("app.pokeapi_service.check_health", return_value=(True, "reachable")):
        resp = client.get("/health")
        data = resp.get_json()
        assert resp.status_code == 503
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"]["ok"] is False


def test_health_degraded_when_pokeapi_down(client):
    with patch("app.db.check_health", return_value=(True, "connected")), \
         patch("app.pokeapi_service.check_health", return_value=(False, "timeout")):
        resp = client.get("/health")
        data = resp.get_json()
        assert resp.status_code == 503
        assert data["status"] == "degraded"


def test_status_page_returns_html(client):
    with patch("app.db.check_health", return_value=(True, "connected")), \
         patch("app.pokeapi_service.check_health", return_value=(True, "reachable")):
        resp = client.get("/status")
        assert resp.status_code == 200
        assert b"System Status" in resp.data
