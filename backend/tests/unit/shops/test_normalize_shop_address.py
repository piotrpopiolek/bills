"""Shop address normalization: empty input, semicolon, street prefix. No network."""

import pytest

from src.shops.normalization import normalize_shop_address


@pytest.mark.parametrize(
    ("raw_address", "expected"),
    [
        pytest.param(None, None, id="none"),
        pytest.param("", None, id="empty"),
        pytest.param("   ", None, id="blank"),
        pytest.param("   ,   ,   ", None, id="commas-only"),
        pytest.param(
            "UL. Akacjowa 1, 62-023 Gądki",
            "ul. akacjowa 1 62-023 gądki",
            id="receipt-gadki",
        ),
        pytest.param(
            "ul. Ostrowska 122, 63-700 Krotoszyn; ul. Starołęcka 219, 61-341 Poznań",
            "ul. ostrowska 122 63-700 krotoszyn",
            id="semicolon-keeps-first",
        ),
        pytest.param(
            "ul. pierwsza 1, 00-000 miasto1; ul. druga 2, 11-111 miasto2",
            "ul. pierwsza 1 00-000 miasto1",
            id="semicolon-second-address-dropped",
        ),
        pytest.param(
            "ul. Starołęcka 219, 61-341 Poznań",
            "ul. starołęcka 219 61-341 poznań",
            id="receipt-poznan",
        ),
        pytest.param(
            "UL. TESTOWA 1, 00-000 WARSZAWA",
            "ul. testowa 1 00-000 warszawa",
            id="lowercase",
        ),
        pytest.param(
            "ul. testowa, 1, 00-000, warszawa",
            "ul. testowa 1 00-000 warszawa",
            id="commas-removed",
        ),
        pytest.param(
            "ul.  testowa   1   00-000   warszawa",
            "ul. testowa 1 00-000 warszawa",
            id="collapse-spaces",
        ),
        pytest.param(
            "OS. TESTOWE 1, 00-000 WARSZAWA",
            "ul. testowe 1 00-000 warszawa",
            id="prefix-os",
        ),
        pytest.param(
            "AL. TESTOWA 1, 00-000 WARSZAWA",
            "ul. testowa 1 00-000 warszawa",
            id="prefix-al",
        ),
        pytest.param(
            "PL. TESTOWY 1, 00-000 WARSZAWA",
            "ul. testowy 1 00-000 warszawa",
            id="prefix-pl",
        ),
        pytest.param(
            "ULICA TESTOWA 1, 00-000 WARSZAWA",
            "ul. testowa 1 00-000 warszawa",
            id="prefix-ulica",
        ),
        pytest.param(
            "OSIEDLE TESTOWE 1, 00-000 WARSZAWA",
            "ul. testowe 1 00-000 warszawa",
            id="prefix-osiedle",
        ),
        pytest.param(
            "ALEJA TESTOWA 1, 00-000 WARSZAWA",
            "ul. testowa 1 00-000 warszawa",
            id="prefix-aleja",
        ),
        pytest.param(
            "PLAC TESTOWY 1, 00-000 WARSZAWA",
            "ul. testowy 1 00-000 warszawa",
            id="prefix-plac",
        ),
        pytest.param(
            "ul. testowa 1a, 00-000 warszawa",
            "ul. testowa 1a 00-000 warszawa",
            id="building-with-letter",
        ),
        pytest.param(
            "ul. testowa 1 warszawa 00-000",
            "ul. testowa 1 00-000 warszawa",
            id="postal-code-moved-before-city",
        ),
    ],
)
def test_normalize_shop_address(raw_address: str | None, expected: str | None) -> None:
    assert normalize_shop_address(raw_address) == expected


def test_normalize_shop_address_is_idempotent() -> None:
    once = normalize_shop_address("UL. Testowa 1, 00-000 Warszawa")
    assert normalize_shop_address(once) == once
    assert once == "ul. testowa 1 00-000 warszawa"
