from src.common.exceptions import AppError


class EmbeddingError(AppError):
    """The embedding model returned a vector this catalog cannot store."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)
