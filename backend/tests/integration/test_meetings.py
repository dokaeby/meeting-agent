from conftest import signup


def create_meeting(client, org):
    result = client.post(
        f"/api/v1/organizations/{org}/meetings",
        json={
            "title": "제품 회의",
            "start_at": "2026-11-10T10:00:00+09:00",
            "timezone": "Asia/Seoul",
        },
    )
    assert result.status_code == 201, result.text
    return result.json()["id"]


def test_minutes_approval_and_idempotent_delivery(client, owner):
    user, org = owner
    meeting = create_meeting(client, org)
    base = f"/api/v1/organizations/{org}/meetings/{meeting}"
    assert (
        client.put(base + "/recipients", json=[{"user_id": user["id"], "email": True}]).status_code
        == 200
    )
    upload = client.post(
        base + "/source",
        files={"file": ("meeting.txt", "출시 준비를 논의했습니다.".encode(), "text/plain")},
    )
    assert upload.status_code == 202, upload.text
    # Explicit test-mode execution is separate from production worker dispatch.
    from meeting_agent.jobs.runner import run_pending

    run_pending(client.app.state.settings, client.app.state.factory)
    doc = client.get(base + "/minutes").json()
    assert doc["version"] == 1, doc
    assert client.post(base + "/send", json={"version": 1}).status_code == 409
    assert client.post(base + "/approve", json={"version": 1}).status_code == 200
    assert client.get(base + "/minutes/1/pdf").content.startswith(b"%PDF")
    first = client.post(base + "/send", json={"version": 1})
    second = client.post(base + "/send", json={"version": 1})
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    run_pending(client.app.state.settings, client.app.state.factory)
    assert (
        client.get(f"/api/v1/organizations/{org}/deliveries").json()["items"][0]["status"]
        == "accepted"
    )


def test_recipient_change_invalidates_approval(client, owner):
    user, org = owner
    meeting = create_meeting(client, org)
    base = f"/api/v1/organizations/{org}/meetings/{meeting}"
    client.put(base + "/recipients", json=[{"user_id": user["id"]}])
    client.post(base + "/source", files={"file": ("m.txt", b"Launch discussion", "text/plain")})
    from meeting_agent.jobs.runner import run_pending

    run_pending(client.app.state.settings, client.app.state.factory)
    assert client.post(base + "/approve", json={"version": 1}).status_code == 200
    client.put(base + "/recipients", json=[{"user_id": user["id"], "email": False, "kakao": True}])
    assert client.post(base + "/send", json={"version": 1}).status_code == 409


def test_cross_tenant_and_invalid_upload(client, owner):
    _, org = owner
    meeting = create_meeting(client, org)
    base = f"/api/v1/organizations/{org}/meetings/{meeting}"
    assert (
        client.post(
            base + "/source", files={"file": ("../m.exe", b"MZbad", "application/octet-stream")}
        ).status_code
        == 422
    )
    client.cookies.clear()
    signup(client, "intruder@example.com")
    assert client.get(base).status_code == 404


def test_recipient_change_revokes_publication(client, owner):
    user, org = owner
    meeting = create_meeting(client, org)
    base = f"/api/v1/organizations/{org}/meetings/{meeting}"
    client.put(base + "/recipients", json=[{"user_id": user["id"]}])
    client.post(base + "/source", files={"file": ("m.txt", b"Launch discussion", "text/plain")})
    from meeting_agent.jobs.runner import run_pending

    run_pending(client.app.state.settings, client.app.state.factory)
    client.post(base + "/approve", json={"version": 1})
    client.put(base + "/recipients", json=[{"user_id": user["id"], "kakao": True}])
    assert client.get(base + "/minutes").json()["published"] is False
