from __future__ import annotations

from typing import Iterator, Protocol


class TranslationError(Exception):
    """Ошибка перевода, пригодная для показа пользователю."""

    def __init__(self, message: str, *, kind: str = "generic") -> None:
        super().__init__(message)
        self.kind = kind


class Translator(Protocol):
    def translate_stream(self, text: str, src: str, dst: str) -> Iterator[str]: ...


LANG_NAMES = {"ru": "Russian", "en": "English"}


def build_system_prompt(src: str, dst: str) -> str:
    src_name = LANG_NAMES.get(src, src)
    dst_name = LANG_NAMES.get(dst, dst)
    return (
        f"You are a professional translator from {src_name} to {dst_name}. "
        "Output ONLY the translation, with no comments, no quotation marks, "
        "no prefixes, no explanations. Preserve the original formatting, line "
        "breaks, punctuation, proper names, URLs, code, and numbers exactly. "
        "Use natural, idiomatic phrasing in the target language."
    )
