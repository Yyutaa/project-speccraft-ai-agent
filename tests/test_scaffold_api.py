from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_health_check_is_available() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "speccraft-project-scaffold",
    }


def test_scaffold_describes_eight_unimplemented_stages() -> None:
    response = client.get("/api/scaffold")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "project-scaffold"
    assert len(payload["stages"]) == 8
    assert all(stage["implemented"] is False for stage in payload["stages"])
    assert payload["stages"][0]["id"] == "requirement_context"
    assert payload["stages"][-1]["id"] == "artifact_publication"
