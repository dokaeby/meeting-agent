from conftest import signup


def test_auth_and_csrf(client):
    assert client.get("/api/v1/auth/session").status_code == 401
    signup(client)
    del client.headers["X-CSRF-Token"]
    assert client.post("/api/v1/organizations", json={"name": "차단"}).status_code == 403


def test_tenant_cannot_read_another_company(client, owner):
    _, org = owner
    client.cookies.clear()
    signup(client, "other@example.com")
    assert client.get(f"/api/v1/organizations/{org}/members").status_code == 404


def test_invitation_is_email_bound_and_single_use(client, owner):
    _, org = owner
    result = client.post(
        f"/api/v1/organizations/{org}/invitations",
        json={"email": "staff@example.com", "role": "member"},
    )
    assert result.status_code == 201, result.text
    token = result.json()["test_token"]
    client.cookies.clear()
    signup(client, "wrong@example.com")
    assert client.post("/api/v1/invitations/accept", json={"token": token}).status_code == 403
    client.cookies.clear()
    signup(client, "staff@example.com")
    assert client.post("/api/v1/invitations/accept", json={"token": token}).status_code == 200
    assert client.post("/api/v1/invitations/accept", json={"token": token}).status_code == 400


def test_cannot_remove_last_admin(client, owner):
    user, org = owner
    assert (
        client.patch(
            f"/api/v1/organizations/{org}/members/{user['id']}",
            json={"role": "member", "active": True},
        ).status_code
        == 409
    )
