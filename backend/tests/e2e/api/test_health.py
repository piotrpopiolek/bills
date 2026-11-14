"""GET /health reports the process. It does not open the database or Telegram."""

from httpx import ASGITransport, AsyncClient


async def test_health_returns_ok() -> None:
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "bills-api"}
