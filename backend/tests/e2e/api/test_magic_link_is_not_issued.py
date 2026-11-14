"""Public HTTP must not mint a magic-link URL."""

from httpx import ASGITransport, AsyncClient


def test_magic_link_route_is_not_registered() -> None:
    from main import app

    for route in app.routes:
        path = getattr(route, "path", "") or ""
        methods = getattr(route, "methods", None) or set()
        assert not (
            path.rstrip("/").endswith("/auth/magic-link") and "POST" in methods
        ), f"POST {path} must not issue login URLs"


async def test_unauthenticated_magic_link_post_returns_404() -> None:
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/magic-link",
            json={"telegram_user_id": 8100001001},
        )

    assert response.status_code == 404
    body = response.text
    assert "magic_link" not in body
    assert "auth/verify?token=" not in body
