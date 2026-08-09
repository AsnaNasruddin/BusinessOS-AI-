async def _register(
    client,
    email="jordan@example.com",
    password="correcthorsebatterystaple",
    full_name="Jordan Avery",
):
    return await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


async def test_register_creates_user_and_owner_org(client):
    response = await _register(client)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    me_body = me.json()
    assert me_body["user"]["email"] == "jordan@example.com"
    assert len(me_body["memberships"]) == 1
    assert me_body["memberships"][0]["role"] == "owner"


async def test_duplicate_email_register_is_rejected(client):
    await _register(client)
    response = await _register(client)
    assert response.status_code == 409


async def test_register_requires_min_length_password(client):
    response = await _register(client, password="short")
    assert response.status_code == 422


async def test_login_with_correct_password(client):
    await _register(client)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "jordan@example.com", "password": "correcthorsebatterystaple"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_with_wrong_password_is_rejected(client):
    await _register(client)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "jordan@example.com", "password": "wrong password"},
    )
    assert response.status_code == 401


async def test_login_with_unknown_email_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert response.status_code == 401


async def test_me_without_token_is_rejected(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_issues_new_access_token(client):
    register_response = await _register(client)
    refresh_token = register_response.json()["refresh_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    new_access_token = response.json()["access_token"]

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_access_token}"}
    )
    assert me.status_code == 200


async def test_access_token_rejected_by_refresh_endpoint(client):
    register_response = await _register(client)
    access_token = register_response.json()["access_token"]

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401
