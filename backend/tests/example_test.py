"""
Example test file demonstrating pytest usage patterns.
This serves as a template for future tests.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_example_health_check(client: AsyncClient):
    """Example test for health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
@pytest.mark.unit
async def test_example_unit_test():
    """Example unit test."""
    # Arrange
    value = 2 + 2

    # Act
    result = value

    # Assert
    assert result == 4


@pytest.mark.parametrize(
    "input_value,expected",
    [
        (1, 2),
        (2, 4),
        (3, 6),
    ],
)
@pytest.mark.unit
def test_example_parameterized(input_value: int, expected: int):
    """Example parameterized test."""
    assert input_value * 2 == expected
