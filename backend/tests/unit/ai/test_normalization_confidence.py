"""A catalog name without a category is not a confident categorization."""

from src.ai.confidence import normalization_confidence


def test_catalog_category_is_fully_confident() -> None:
    score, confident = normalization_confidence(
        product_category_id=4,
        assigned_category_id=4,
        fallback_category_id=9,
        ocr_confidence=0.8,
    )

    assert score == 1.0
    assert confident is True


def test_matched_name_without_category_is_not_fully_confident() -> None:
    score, confident = normalization_confidence(
        product_category_id=None,
        assigned_category_id=9,
        fallback_category_id=9,
        ocr_confidence=0.8,
    )

    assert score == 0.8 * 0.5
    assert confident is False


def test_generative_category_keeps_the_model_penalty() -> None:
    score, confident = normalization_confidence(
        product_category_id=None,
        assigned_category_id=4,
        fallback_category_id=9,
        ocr_confidence=0.8,
    )

    assert score == 0.8 * 0.7
    assert confident is True
