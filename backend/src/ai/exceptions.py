class AIError(Exception):
    """Base exception for AI module."""

    pass


class CategorizationError(AIError):
    """Raised when categorization fails."""

    pass
