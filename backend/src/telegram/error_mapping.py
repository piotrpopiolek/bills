"""
Mapping of domain exceptions to user-friendly Telegram messages.

This module provides a centralized way to translate domain exceptions
into messages that are appropriate for Telegram bot users.
"""

from src.common.exceptions import (
    AppError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    UserCreationError,
)
from src.reports.exceptions import InvalidDateRangeError, InvalidMonthFormatError


def get_user_message(error: Exception) -> str:
    """
    Map domain exception to user-friendly Telegram message.

    Args:
        error: Domain exception to map

    Returns:
        User-friendly message in Polish

    Note:
        If error is not a known domain exception, returns generic message.
    """
    if isinstance(error, ResourceAlreadyExistsError):
        return "Użytkownik już istnieje. Spróbuj /login aby otrzymać link do logowania."

    if isinstance(error, UserCreationError):
        return f"Wystąpił błąd podczas rejestracji: {error.reason}"

    if isinstance(error, ResourceNotFoundError):
        return "Nie znaleziono zasobu. Spróbuj ponownie."

    if isinstance(error, InvalidDateRangeError):
        return str(error)  # Error message is already user-friendly in Polish

    if isinstance(error, InvalidMonthFormatError):
        return str(error)  # Error message is already user-friendly in Polish

    if isinstance(error, AppError):
        return f"Wystąpił błąd: {error.message}"

    # Generic fallback for unknown exceptions
    return "Wystąpił nieoczekiwany błąd. Spróbuj ponownie później."
