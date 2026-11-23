def catalog_name_without_category(
    *, has_catalog_product: bool, category_id: int | None
) -> bool:
    """A catalog hit with no category does not call the generative model."""
    return has_catalog_product and category_id is None


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
