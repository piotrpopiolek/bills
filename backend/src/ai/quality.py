"""Quality fixtures for receipt lines. The hit bar is fixed before the rows.

A known alias, or a vector at or above the catalog threshold, is a hit only
when the generative model is not called. A vector below the threshold is not
scored; the check is that the recovered names are in the prompt.

Run from backend/: python -m src.ai.quality
"""

from dataclasses import dataclass
from typing import Literal

from src.ai.catalog_prompt import build_categorization_prompt
from src.config import settings
from src.product_indexes.catalog import CatalogHit

# Set before the fixture rows. Every alias and above-threshold vector must hit.
HIT_RATE_MINIMUM = 1.0

Route = Literal["alias", "vector", "below"]


@dataclass(frozen=True)
class ReceiptCase:
    text: str
    route: Route
    expected_name: str
    similarity: float | None = None
    category_name: str | None = None
    prompt_names: tuple[str, ...] = ()


# Synthetic Polish receipt lines. Do not lower HIT_RATE_MINIMUM to fit a row.
FIXTURES: tuple[ReceiptCase, ...] = (
    ReceiptCase(
        text="MLEKO UHT 3,2% 1L",
        route="alias",
        expected_name="mleko 3.2%",
        category_name="Nabiał i Jaja",
    ),
    ReceiptCase(
        text="CHLEB PSZENNY KROJONY",
        route="alias",
        expected_name="chleb pszenny",
        category_name="Pieczywo",
    ),
    ReceiptCase(
        text="JOGURT NATURALNY 400G",
        route="vector",
        expected_name="jogurt naturalny",
        similarity=0.91,
        category_name="Nabiał i Jaja",
    ),
    ReceiptCase(
        text="BANANY LUZEM",
        route="vector",
        expected_name="banany",
        similarity=0.88,
        category_name="Owoce",
    ),
    ReceiptCase(
        text="PŁYN DO NACZYŃ 500ML",
        route="below",
        expected_name="płyn do naczyń",
        similarity=0.42,
        category_name="Dom i Ogród",
        prompt_names=("płyn do naczyń", "płyn do szyb"),
    ),
)


@dataclass(frozen=True)
class QualityReport:
    hits: int
    scored: int
    rate: float
    prompt_checks: int
    misses: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return (
            self.scored > 0 and self.rate + 1e-9 >= HIT_RATE_MINIMUM and not self.misses
        )


def score(cases: tuple[ReceiptCase, ...] = FIXTURES) -> QualityReport:
    """Count catalog hits. The generative model is not used."""
    hits = 0
    scored = 0
    prompt_checks = 0
    misses: list[str] = []
    threshold = settings.AI_VECTOR_SIMILARITY_THRESHOLD
    for case in cases:
        if case.route == "below":
            prompt_checks += 1
            if _below_prompt_ok(case, threshold):
                continue
            misses.append(case.text)
            continue
        scored += 1
        if _catalog_hit(case, threshold):
            hits += 1
            continue
        misses.append(case.text)
    rate = hits / scored if scored else 0.0
    return QualityReport(hits, scored, rate, prompt_checks, tuple(misses))


def _catalog_hit(case: ReceiptCase, threshold: float) -> bool:
    if case.route == "alias":
        return True
    if case.similarity is None:
        return False
    return case.similarity >= threshold


def _below_prompt_ok(case: ReceiptCase, threshold: float) -> bool:
    if case.similarity is None or case.similarity >= threshold:
        return False
    names = case.prompt_names or (case.expected_name,)
    hits = tuple(
        CatalogHit(
            name=name,
            category_name=case.category_name,
            similarity=case.similarity,
        )
        for name in names
    )
    prompt = build_categorization_prompt(
        cleaned_text=case.text,
        category_suggestion=None,
        shop_name=None,
        hits=list(hits),
        category_names=[case.category_name] if case.category_name else [],
    )
    return all(name in prompt for name in names)


def main() -> int:
    report = score()
    print(
        f"trafienia {report.hits}/{report.scored} ({report.rate:.2f}), "
        f"próg {HIT_RATE_MINIMUM:.2f}"
    )
    print(f"poniżej progu: {report.prompt_checks}")
    if report.misses:
        print("pudła: " + ", ".join(report.misses))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
