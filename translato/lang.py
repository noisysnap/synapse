from __future__ import annotations


def _is_cyrillic(ch: str) -> bool:
    return "Ѐ" <= ch <= "ӿ"


def detect_direction(text: str) -> tuple[str, str]:
    """Return (src, dst) language codes: either ('ru', 'en') or ('en', 'ru').

    Rule: share of Cyrillic letters among all letters > 30% → ru→en, else en→ru.
    If there are no letters at all, default to en→ru.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en", "ru"
    cyr = sum(1 for c in letters if _is_cyrillic(c))
    ratio = cyr / len(letters)
    if ratio > 0.30:
        return "ru", "en"
    return "en", "ru"


LANG_LABELS = {"ru": "RU", "en": "EN"}


def direction_label(src: str, dst: str) -> str:
    return f"{LANG_LABELS.get(src, src.upper())} → {LANG_LABELS.get(dst, dst.upper())}"
