"""Shop name normalization: case, quotes, and empty input. No network."""

import pytest

from src.shops.normalization import normalize_shop_name


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        pytest.param("DINO POLSKA S.A.", "dino polska s.a.", id="receipt-dino"),
        pytest.param('"POIN" SP.Z O.O.', "poin sp.z o.o.", id="quotes-around-name"),
        pytest.param("  ALDI  ", "aldi", id="trim"),
        pytest.param("ALDI Sp. z o.o.", "aldi sp. z o.o.", id="mixed-case-legal-form"),
        pytest.param("SkLeP TeSt", "sklep test", id="lowercase"),
        pytest.param("\tsklep\n", "sklep", id="trim-tabs-and-newlines"),
        pytest.param('"sklep"', "sklep", id="double-quotes"),
        pytest.param("'sklep'", "sklep", id="single-quotes"),
        pytest.param(
            "'sklep' z 'cudzysłowami'",
            "sklep z cudzysłowami",
            id="quotes-between-words",
        ),
        pytest.param(
            "sklep   z   wieloma   spacjami",
            "sklep z wieloma spacjami",
            id="collapse-spaces",
        ),
        pytest.param("", "", id="empty"),
        pytest.param(None, "", id="none"),
        pytest.param("   ", "", id="blank"),
        pytest.param("\t\n\r", "", id="whitespace-only"),
        pytest.param("Żabka Polska S.A.", "żabka polska s.a.", id="receipt-zabka"),
        pytest.param(
            "Sklep z polskimi znakami: ąęćłńóśźż",
            "sklep z polskimi znakami: ąęćłńóśźż",
            id="polish-letters",
        ),
    ],
)
def test_normalize_shop_name(raw_name: str | None, expected: str) -> None:
    assert normalize_shop_name(raw_name) == expected


def test_normalize_shop_name_is_idempotent() -> None:
    once = normalize_shop_name('  "DINO POLSKA" S.A.  ')
    assert normalize_shop_name(once) == once
    assert once == "dino polska s.a."
