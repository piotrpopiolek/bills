from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# NOTE: W MVP endpoint OCR jest stateless - nie zapisuje danych do bazy.
# Dane są zwracane jako JSON w odpowiedzi HTTP.
# W kontekście Telegram Bot, dane są zapisywane do bill_items (is_verified=False).
# Modele bazodanowe dla OCR mogą być dodane w przyszłości, jeśli będzie potrzeba
# przechowywania historii ekstrakcji lub cache'owania wyników.
