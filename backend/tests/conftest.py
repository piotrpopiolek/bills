"""Shared pytest hooks. Database fixtures connect only when a test asks."""

from collections.abc import Callable

import pytest


def _disable_coverage_floor_for_unit(config: pytest.Config) -> None:
    """The suite floor applies to the full run, not to pytest -m unit."""
    markexpr = (getattr(config.option, "markexpr", None) or "").strip()
    if markexpr != "unit":
        return
    if hasattr(config.option, "cov_fail_under"):
        config.option.cov_fail_under = 0
    plugin = config.pluginmanager.get_plugin("_cov")
    options = getattr(plugin, "options", None)
    if options is not None and hasattr(options, "cov_fail_under"):
        options.cov_fail_under = 0


def pytest_configure(config: pytest.Config) -> None:
    markexpr = (getattr(config.option, "markexpr", None) or "").strip()
    workers = getattr(config.option, "numprocesses", None)
    if workers not in (None, 0) and markexpr != "unit":
        raise pytest.UsageError(
            "pytest-xdist (-n) is only for unit tests. "
            "Integration and e2e share one Postgres and run serially, without -n."
        )
    _disable_coverage_floor_for_unit(config)


def pytest_sessionstart(session: pytest.Session) -> None:
    _disable_coverage_floor_for_unit(session.config)


def pytest_ignore_collect(collection_path, config: pytest.Config):
    """Unit runs do not import integration or e2e modules, so they need no database."""
    markexpr = (getattr(config.option, "markexpr", None) or "").strip()
    if markexpr != "unit":
        return False
    path = collection_path.as_posix()
    return "/tests/integration/" in path or "/tests/e2e/" in path


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        path = item.path.as_posix()
        if "/tests/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/tests/e2e/" in path:
            item.add_marker(pytest.mark.e2e)

        if "/telegram/" in path:
            item.add_marker(pytest.mark.telegram)
        if "magic_link" in path:
            item.add_marker(pytest.mark.auth)

    _disable_coverage_floor_for_unit(config)


def _kind_for(path: str) -> str:
    if "/tests/unit/" in path:
        return "unit"
    if "/tests/integration/" in path:
        return "integration"
    if "/tests/e2e/" in path:
        return "e2e"
    return "other"


@pytest.fixture
async def db_engine():
    from tests.database import create_test_engine

    engine = create_test_engine()
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    from tests.database import session_factory

    maker = session_factory(db_engine)
    async with maker() as session:
        yield session


@pytest.fixture
async def owned(db_session) -> Callable:
    """Open a user by an explicit external id and delete only that user's rows."""
    from tests.support import create_user, delete_owned_user

    external_ids: list[int] = []

    async def open_user(external_id: int):
        external_ids.append(external_id)
        return await create_user(db_session, external_id)

    yield open_user

    for external_id in external_ids:
        await delete_owned_user(db_session, external_id)
