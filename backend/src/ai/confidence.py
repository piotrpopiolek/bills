def normalization_confidence(
    *,
    product_category_id: int | None,
    assigned_category_id: int,
    fallback_category_id: int,
    ocr_confidence: float,
) -> tuple[float, bool]:
    """Confidence is 1 only when the category comes from the matched catalog row."""
    if product_category_id is not None and product_category_id == assigned_category_id:
        return 1.0, True
    if assigned_category_id == fallback_category_id:
        return ocr_confidence * 0.5, False
    return ocr_confidence * 0.7, True
