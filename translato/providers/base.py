from __future__ import annotations

from typing import Protocol


class TranslationError(Exception):
    """Ошибка перевода, пригодная для показа пользователю."""

    def __init__(self, message: str, *, kind: str = "generic") -> None:
        super().__init__(message)
        self.kind = kind


class Translator(Protocol):
    def translate(self, text: str, src: str, dst: str) -> str: ...
