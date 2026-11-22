"""The categorization prompt contains the catalog names recovered before it."""

from src.ai.catalog_prompt import build_categorization_prompt, hits_for_categorization
from src.product_indexes.catalog import CatalogHit


def test_prompt_contains_retrieved_names_and_categories() -> None:
    text = build_categorization_prompt(
        cleaned_text="MLEKO 3.2",
        category_suggestion="nabial",
        shop_name="Dino",
        hits=[
            CatalogHit(name="mleko 3.2%", category_name="Nabiał", similarity=0.62),
            CatalogHit(name="kefir naturalny", category_name="Nabiał", similarity=0.41),
        ],
        category_names=["Nabiał", "Inne"],
    )

    assert "mleko 3.2%" in text
    assert "kefir naturalny" in text
    assert "Nabiał" in text
    assert "MLEKO 3.2" in text
    assert "Dino" in text


def test_prompt_says_when_the_catalog_is_empty() -> None:
    text = build_categorization_prompt(
        cleaned_text="nieznany produkt",
        category_suggestion=None,
        shop_name=None,
        hits=[],
        category_names=["Inne"],
    )

    assert "Odzyskany katalog:\nbrak" in text
    assert "nieznany produkt" in text


def test_deleted_category_still_puts_the_catalog_name_in_the_prompt() -> None:
    hits = hits_for_categorization("mleko 3.2%", [])
    text = build_categorization_prompt(
        cleaned_text="MLEKO",
        category_suggestion=None,
        shop_name=None,
        hits=hits,
        category_names=["Nabiał", "Inne"],
    )

    assert "mleko 3.2%" in text
    assert "brak kategorii" in text
