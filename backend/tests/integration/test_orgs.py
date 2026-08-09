async def _register(client, email, full_name):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorsebatterystaple", "full_name": full_name},
    )
    body = response.json()
    return body["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def test_list_orgs_includes_auto_created_workspace(client):
    token = await _register(client, "jordan@example.com", "Jordan Avery")
    response = await client.get("/api/v1/orgs", headers=_auth(token))
    assert response.status_code == 200
    orgs = response.json()
    assert len(orgs) == 1
    assert orgs[0]["my_role"] == "owner"


async def test_create_second_org(client):
    token = await _register(client, "jordan@example.com", "Jordan Avery")
    response = await client.post(
        "/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(token)
    )
    assert response.status_code == 201
    assert response.json()["slug"] == "acme-robotics"

    orgs = (await client.get("/api/v1/orgs", headers=_auth(token))).json()
    assert len(orgs) == 2


async def test_org_slugs_are_deduplicated(client):
    token = await _register(client, "jordan@example.com", "Jordan Avery")
    await client.post("/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(token))
    second = await client.post("/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(token))
    assert second.json()["slug"] == "acme-robotics-2"


async def test_get_org_detail_includes_members(client):
    token = await _register(client, "jordan@example.com", "Jordan Avery")
    org = (
        await client.post("/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(token))
    ).json()

    response = await client.get(f"/api/v1/orgs/{org['id']}", headers=_auth(token))
    assert response.status_code == 200
    detail = response.json()
    assert len(detail["members"]) == 1
    assert detail["members"][0]["email"] == "jordan@example.com"


async def test_non_member_cannot_view_org(client):
    owner_token = await _register(client, "jordan@example.com", "Jordan Avery")
    org = (
        await client.post(
            "/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(owner_token)
        )
    ).json()

    outsider_token = await _register(client, "outsider@example.com", "Sam Rivera")
    response = await client.get(f"/api/v1/orgs/{org['id']}", headers=_auth(outsider_token))
    assert response.status_code == 403


async def test_invite_then_accept_creates_membership(client):
    owner_token = await _register(client, "jordan@example.com", "Jordan Avery")
    org = (
        await client.post(
            "/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(owner_token)
        )
    ).json()

    # invite an email that has no account yet
    invite = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "new.hire@example.com", "role": "member"},
        headers=_auth(owner_token),
    )
    assert invite.status_code == 201
    invite_token = invite.json()["invite_token"]

    accept = await client.post(
        "/api/v1/orgs/accept-invite",
        json={
            "invite_token": invite_token,
            "full_name": "New Hire",
            "password": "correcthorsebatterystaple",
        },
    )
    assert accept.status_code == 200
    new_hire_token = accept.json()["access_token"]

    detail = (await client.get(f"/api/v1/orgs/{org['id']}", headers=_auth(new_hire_token))).json()
    emails = {m["email"] for m in detail["members"]}
    assert "new.hire@example.com" in emails


async def test_member_role_cannot_invite(client):
    owner_token = await _register(client, "jordan@example.com", "Jordan Avery")
    org = (
        await client.post(
            "/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(owner_token)
        )
    ).json()

    invite = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "new.hire@example.com", "role": "member"},
        headers=_auth(owner_token),
    )
    invite_token = invite.json()["invite_token"]
    await client.post(
        "/api/v1/orgs/accept-invite",
        json={
            "invite_token": invite_token,
            "full_name": "New Hire",
            "password": "correcthorsebatterystaple",
        },
    )
    member_token = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "new.hire@example.com", "password": "correcthorsebatterystaple"},
        )
    ).json()["access_token"]

    response = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "another@example.com", "role": "member"},
        headers=_auth(member_token),
    )
    assert response.status_code == 403


async def test_inviting_existing_member_conflicts(client):
    owner_token = await _register(client, "jordan@example.com", "Jordan Avery")
    org = (
        await client.post(
            "/api/v1/orgs", json={"name": "Acme Robotics"}, headers=_auth(owner_token)
        )
    ).json()

    # owner is already a member — inviting the same email should 409
    response = await client.post(
        f"/api/v1/orgs/{org['id']}/members",
        json={"email": "jordan@example.com", "role": "member"},
        headers=_auth(owner_token),
    )
    assert response.status_code == 409
