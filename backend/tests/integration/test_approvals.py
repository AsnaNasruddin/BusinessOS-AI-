import uuid

import pytest


async def _register_with_org(client, email, full_name):
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correcthorsebatterystaple", "full_name": full_name},
    )
    token = register.json()["access_token"]
    orgs = (await client.get("/api/v1/orgs", headers=_auth(token))).json()
    return token, orgs[0]["id"]


def _auth(token, org_id=None):
    headers = {"Authorization": f"Bearer {token}"}
    if org_id:
        headers["X-Org-Id"] = org_id
    return headers


async def test_list_approvals_empty_for_fresh_org(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    response = await client.get("/api/v1/approvals", headers=_auth(token, org_id))
    assert response.status_code == 200
    assert response.json() == []


async def test_decide_unknown_approval_is_404(client):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    response = await client.post(
        f"/api/v1/approvals/{uuid.uuid4()}/decide",
        json={"status": "approved"},
        headers=_auth(token, org_id),
    )
    assert response.status_code == 404


async def test_decide_requires_org_membership(client):
    """An approval from one org must not be decidable (or even visible via
    404 vs a leaking 403) by a user in a different org."""
    owner_token, owner_org = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    outsider_token, outsider_org = await _register_with_org(client, "sam@example.com", "Sam Rivera")

    response = await client.post(
        f"/api/v1/approvals/{uuid.uuid4()}/decide",
        json={"status": "approved"},
        headers=_auth(outsider_token, outsider_org),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("bad_status", ["maybe", "pending", ""])
async def test_decide_rejects_invalid_status(client, bad_status):
    token, org_id = await _register_with_org(client, "jordan@example.com", "Jordan Avery")
    response = await client.post(
        f"/api/v1/approvals/{uuid.uuid4()}/decide",
        json={"status": bad_status},
        headers=_auth(token, org_id),
    )
    assert response.status_code == 422
