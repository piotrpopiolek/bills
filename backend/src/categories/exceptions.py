from src.common.exceptions import AppError


class CategoryCycleError(AppError):
    def __init__(self):
        super().__init__("Category cannot be its own parent or child of its own child.")


class CategoryHasChildrenError(AppError):
    def __init__(self):
        super().__init__("Cannot delete category containing subcategories.")
