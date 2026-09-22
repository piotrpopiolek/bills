"""
Custom domain exceptions for the reports module.
"""


class InvalidDateRangeError(Exception):
    """Raised when a date is in the future or outside valid range."""

    def __init__(self, message: str = "Data nie może być w przyszłości"):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


class InvalidMonthFormatError(Exception):
    """Raised when month format is invalid (must be YYYY-MM)."""

    def __init__(
        self, message: str = "Nieprawidłowy format miesiąca. Oczekiwany format: YYYY-MM"
    ):
        self.message = message
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message
