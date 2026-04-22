from __future__ import annotations

from typing import Iterator, Protocol


class TranslationError(Exception):
    """Ошибка перевода, пригодная для показа пользователю."""

    def __init__(self, message: str, *, kind: str = "generic") -> None:
        super().__init__(message)
        self.kind = kind


class Translator(Protocol):
    def translate_stream(self, text: str, src: str, dst: str) -> Iterator[str]: ...


LANG_NAMES = {
    "ru": "Russian",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
    "ar": "Arabic",
    "tr": "Turkish",
    "pl": "Polish",
    "uk": "Ukrainian",
    "nl": "Dutch",
    "sv": "Swedish",
    "cs": "Czech",
    "hi": "Hindi",
    "id": "Indonesian",
    "th": "Thai",
}


def build_system_prompt(src: str, dst: str, extra: str | None = None) -> str:
    src_name = LANG_NAMES.get(src, src)
    dst_name = LANG_NAMES.get(dst, dst)
    base = (
        f"You are a professional translator from {src_name} to {dst_name}. "
        "Output ONLY the translation, with no comments, no quotation marks, "
        "no prefixes, no explanations. Preserve the original formatting, line "
        "breaks, punctuation, proper names, URLs, code, and numbers exactly. "
        "Use natural, idiomatic phrasing in the target language."
    )
    if extra and extra.strip():
        return f"{base}\n\nAdditional user instructions (apply on top of the rules above, do not override them):\n{extra.strip()}"
    return base
