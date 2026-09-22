"""Public HTTP must not issue magic-link login URLs."""

import pytest
from httpx import ASGITransport, AsyncClient
from main import app


def test_magic_link_route_is_not_registered():
    for route in app.routes:
        path = getattr(route, "path", "") or ""
        methods = getattr(route, "methods", None) or set()
        assert not (
            path.rstrip("/").endswith("/auth/magic-link") and "POST" in methods
        ), f"POST {path} must not issue login URLs"


@pytest.mark.asyncio
@pytest.mark.auth
async def test_unauthenticated_magic_link_post_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/auth/magic-link",
            json={"telegram_user_id": 123456789},
        )

    assert response.status_code == 404
    body = response.text
    assert "magic_link" not in body
    assert "auth/verify?token=" not in body
