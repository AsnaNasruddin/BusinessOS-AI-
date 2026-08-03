async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "BusinessOS AI"
