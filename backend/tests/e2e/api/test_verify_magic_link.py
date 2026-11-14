"""Magic-link verification: a live link logs in, an expired or reused one does not."""

import logging
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from tests.support import insert_magic_link

EXPIRED_AT = datetime(2020, 1, 1, tzinfo=UTC)
EXTERNAL_VALID = 8_100_001_101
EXTERNAL_EXPIRED = 8_100_001_102
EXTERNAL_REUSED = 8_100_001_103


def _assert_token_is_absent(
    response, token: str, caplog: pytest.LogCaptureFixture
) -> None:
    assert token not in response.text
    assert "auth/verify?token=" not in response.text
    application_log = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name.startswith("src.")
    )
    assert token not in application_log


async def test_valid_magic_link_logs_in_without_echoing_the_token(
    api_client: AsyncClient,
    db_session,
    owned,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from src.auth.services import AuthService

    user = await owned(EXTERNAL_VALID)
    link, _url = await AuthService(db_session).create_magic_link_for_user(user.id)

    with caplog.at_level(logging.DEBUG):
        response = await api_client.get(
            "/api/auth/verify", params={"token": link.token}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["id"] == user.id
    assert body["user"]["external_id"] == EXTERNAL_VALID
    _assert_token_is_absent(response, link.token, caplog)

    await db_session.refresh(link)
    assert link.used is True


async def test_expired_magic_link_does_not_log_in(
    api_client: AsyncClient,
    db_session,
    owned,
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = await owned(EXTERNAL_EXPIRED)
    token = f"expired-magic-link-{EXTERNAL_EXPIRED}"
    await insert_magic_link(
        db_session,
        user_id=user.id,
        token=token,
        expires_at=EXPIRED_AT,
    )

    with caplog.at_level(logging.DEBUG):
        response = await api_client.get("/api/auth/verify", params={"token": token})

    assert response.status_code == 401
    assert "access_token" not in response.json()
    _assert_token_is_absent(response, token, caplog)


async def test_magic_link_cannot_be_used_twice(
    api_client: AsyncClient,
    db_session,
    owned,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from src.auth.services import AuthService

    user = await owned(EXTERNAL_REUSED)
    link, _url = await AuthService(db_session).create_magic_link_for_user(user.id)

    with caplog.at_level(logging.DEBUG):
        first = await api_client.get("/api/auth/verify", params={"token": link.token})
        second = await api_client.get("/api/auth/verify", params={"token": link.token})

    assert first.status_code == 200
    assert second.status_code == 401
    assert "access_token" not in second.json()
    _assert_token_is_absent(first, link.token, caplog)
    _assert_token_is_absent(second, link.token, caplog)
