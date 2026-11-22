"""Compose the categorization prompt after a catalog search.

LangChain is used only here. The Gemini call stays the ordinary client.
"""

from langchain_core.prompts import PromptTemplate

from src.product_indexes.catalog import CatalogHit

_TEMPLATE = PromptTemplate.from_template(
    """Jesteś ekspertem w kategoryzacji produktów ze sklepów.

Produkt: {product}
Sugerowana kategoria (z OCR): {suggestion}
Sklep: {shop}

Odzyskany katalog:
{catalog}

Dostępne kategorie:
{categories}

Zadanie:
1. Wybierz NAJLEPSZĄ kategorię z listy dostępnych kategorii dla tego produktu.
2. Jeśli żadna kategoria nie pasuje idealnie, zwróć null (nie wymyślaj nowych kategorii).
3. Oceń swoją pewność (confidence) w przedziale 0.0-1.0.
4. Uwzględnij odzyskane nazwy i kategorie, ale nie wymyślaj produktu spoza katalogu.

Zwróć odpowiedź w formacie JSON:
{{
    "category_name": "Nazwa kategorii z listy lub null",
    "confidence": 0.95,
    "reasoning": "Krótkie uzasadnienie wyboru"
}}"""
)


def build_categorization_prompt(
    *,
    cleaned_text: str,
    category_suggestion: str | None,
    shop_name: str | None,
    hits: list[CatalogHit],
    category_names: list[str],
) -> str:
    """Return the prompt text. Retrieved catalog names are included as written."""
    return _TEMPLATE.format(
        product=cleaned_text,
        suggestion=category_suggestion or "brak",
        shop=shop_name or "nieznany",
        catalog=_format_catalog(hits),
        categories=_format_categories(category_names),
    )


def _format_catalog(hits: list[CatalogHit]) -> str:
    if not hits:
        return "brak"
    lines: list[str] = []
    for hit in hits:
        category = hit.category_name or "brak kategorii"
        lines.append(f"- {hit.name} ({category}, podobieństwo {hit.similarity:.2f})")
    return "\n".join(lines)


def _format_categories(names: list[str]) -> str:
    if not names:
        return "brak"
    return "\n".join(f"- {name}" for name in names)
