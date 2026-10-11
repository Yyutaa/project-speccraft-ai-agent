from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_run_api_happy_path_returns_each_server_owned_state() -> None:
    created_response = client.post(
        "/api/runs",
        json={"requirement": "导出大文件时显示进度。"},
    )

    assert created_response.status_code == 201
    created = created_response.json()
    run_id = created["run_id"]
    assert created["status"] == "prd_awaiting_approval"
    assert created["td_draft"] is None
    assert created["delivery_spec"] is None

    read_response = client.get(f"/api/runs/{run_id}")
    assert read_response.status_code == 200
    assert read_response.json() == created

    prd_response = client.post(
        f"/api/runs/{run_id}/approvals/prd",
        json={"revision": created["prd_draft"]["revision"]},
    )
    assert prd_response.status_code == 200
    after_prd = prd_response.json()
    assert after_prd["status"] == "td_awaiting_approval"
    assert after_prd["prd_approval"]["revision"] == 1
    assert after_prd["td_draft"] is not None
    assert after_prd["delivery_spec"] is None

    td_response = client.post(
        f"/api/runs/{run_id}/approvals/td",
        json={"revision": after_prd["td_draft"]["revision"]},
    )
    assert td_response.status_code == 200
    completed = td_response.json()
    assert completed["status"] == "completed"
    assert completed["delivery_spec"]["run_id"] == run_id
    assert completed["delivery_spec"]["prd_revision"] == 1
    assert completed["delivery_spec"]["td_revision"] == 1


def test_td_approval_before_prd_is_rejected_without_state_change() -> None:
    created = client.post(
        "/api/runs", json={"requirement": "导出大文件时显示进度。"}
    ).json()
    run_id = created["run_id"]

    response = client.post(
        f"/api/runs/{run_id}/approvals/td",
        json={"revision": 1},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_run_transition"
    assert client.get(f"/api/runs/{run_id}").json() == created


def test_stale_revision_is_rejected_without_state_change() -> None:
    created = client.post(
        "/api/runs", json={"requirement": "导出大文件时显示进度。"}
    ).json()
    run_id = created["run_id"]

    response = client.post(
        f"/api/runs/{run_id}/approvals/prd",
        json={"revision": 2},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "revision_conflict"
    assert client.get(f"/api/runs/{run_id}").json() == created


def test_stale_td_revision_is_rejected_without_state_change() -> None:
    created = client.post(
        "/api/runs", json={"requirement": "导出大文件时显示进度。"}
    ).json()
    run_id = created["run_id"]
    awaiting_td = client.post(
        f"/api/runs/{run_id}/approvals/prd", json={"revision": 1}
    ).json()

    response = client.post(
        f"/api/runs/{run_id}/approvals/td",
        json={"revision": 2},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "revision_conflict"
    assert client.get(f"/api/runs/{run_id}").json() == awaiting_td


def test_repeated_approval_is_rejected_and_run_remains_unchanged() -> None:
    created = client.post(
        "/api/runs", json={"requirement": "导出大文件时显示进度。"}
    ).json()
    run_id = created["run_id"]
    url = f"/api/runs/{run_id}/approvals/prd"
    body = {"revision": created["prd_draft"]["revision"]}
    accepted = client.post(url, json=body)
    assert accepted.status_code == 200

    rejected = client.post(url, json=body)

    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "invalid_run_transition"
    assert client.get(f"/api/runs/{run_id}").json() == accepted.json()


def test_repeated_td_approval_is_rejected_and_completed_run_remains_unchanged() -> None:
    created = client.post(
        "/api/runs", json={"requirement": "导出大文件时显示进度。"}
    ).json()
    run_id = created["run_id"]
    client.post(f"/api/runs/{run_id}/approvals/prd", json={"revision": 1})
    url = f"/api/runs/{run_id}/approvals/td"
    accepted = client.post(url, json={"revision": 1})
    assert accepted.status_code == 200

    rejected = client.post(url, json={"revision": 1})

    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "invalid_run_transition"
    assert client.get(f"/api/runs/{run_id}").json() == accepted.json()


def test_unknown_run_is_not_found_and_blank_requirement_is_invalid() -> None:
    missing = client.get("/api/runs/does-not-exist")
    blank = client.post("/api/runs", json={"requirement": "  "})

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "run_not_found"
    assert blank.status_code == 422
