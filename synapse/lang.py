from __future__ import annotations

# Популярные языки перевода. Первый — английский (дефолт).
# Вьетнамский присутствует по явному требованию.
POPULAR_LANGUAGES: list[tuple[str, str]] = [
    ("en", "English"),
    ("ru", "Русский"),
    ("es", "Español"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("it", "Italiano"),
    ("pt", "Português"),
    ("zh", "中文"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("vi", "Tiếng Việt"),
    ("ar", "العربية"),
    ("tr", "Türkçe"),
    ("pl", "Polski"),
    ("uk", "Українська"),
    ("nl", "Nederlands"),
    ("sv", "Svenska"),
    ("cs", "Čeština"),
    ("hi", "हिन्दी"),
    ("id", "Bahasa Indonesia"),
    ("th", "ไทย"),
]

LANGUAGE_CODES: set[str] = {code for code, _ in POPULAR_LANGUAGES}

# Человеко-понятные короткие метки для показа в скобках. Там, где ISO-код языка
# расходится с привычным обозначением по стране/письменности, используем
# более узнаваемый вариант (JP вместо JA, KR вместо KO, CN вместо ZH, UA вместо UK).
SHORT_CODE_OVERRIDES: dict[str, str] = {
    "ja": "JP",
    "ko": "KR",
    "zh": "CN",
    "uk": "UA",
    "cs": "CZ",
    "sv": "SE",
    "da": "DK",
}


def short_code(code: str) -> str:
    return SHORT_CODE_OVERRIDES.get(code, code.upper())


def language_display(code: str, name: str) -> str:
    return f"{name} ({short_code(code)})"


def _script_of(ch: str) -> str | None:
    """Вернуть код языка по Unicode-блоку одиночного символа, если он
    однозначно ассоциируется с языком. Для латиницы возвращает None —
    различить, скажем, English и French по буквам без словаря нельзя."""
    cp = ord(ch)
    # Кириллица: основной блок + доп. расширения (в т.ч. украинские буквы).
    if 0x0400 <= cp <= 0x04FF or 0x0500 <= cp <= 0x052F:
        return "ru"
    # Хирагана + катакана → гарантированно японский.
    if 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
        return "ja"
    # Хангыль.
    if (0xAC00 <= cp <= 0xD7AF) or (0x1100 <= cp <= 0x11FF) or (0x3130 <= cp <= 0x318F):
        return "ko"
    # CJK-иероглифы — отдаём китайскому (для чисто иероглифического текста
    # отличить японский от китайского без словаря нельзя).
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
        return "zh"
    # Арабский.
    if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:
        return "ar"
    # Тайский.
    if 0x0E00 <= cp <= 0x0E7F:
        return "th"
    # Деванагари (хинди).
    if 0x0900 <= cp <= 0x097F:
        return "hi"
    return None


def detect_source(text: str) -> str:
    """Определить язык оригинала по скриптам Юникода.

    Для языков с уникальной письменностью (русский, японский, корейский,
    китайский, арабский, тайский, хинди) возвращает конкретный код языка.
    Для латиницы и прочего — 'en' (эвристика без словарей всё равно
    ненадёжна; пользователь всегда может исправить через src-combo).
    """
    counts: dict[str, int] = {}
    total_letters = 0
    for ch in text:
        if not ch.isalpha():
            continue
        total_letters += 1
        lang = _script_of(ch)
        if lang is not None:
            counts[lang] = counts.get(lang, 0) + 1

    if not counts or total_letters == 0:
        return "en"
    # Японский приоритетнее китайского: если нашли хоть одну кану — это
    # точно японский, даже если ханьских иероглифов больше.
    if counts.get("ja", 0) > 0:
        return "ja"
    # Лидирующий по доле скрипт, но только если он занимает заметную часть
    # букв (>30%), иначе считаем текст латинским (en).
    best_lang, best_count = max(counts.items(), key=lambda kv: kv[1])
    if best_count / total_letters > 0.30:
        return best_lang
    return "en"


def resolve_direction(text: str, preferred_dst: str) -> tuple[str, str]:
    """Вычислить направление перевода с учётом предпочитаемого языка.

    Если исходный текст уже на preferred_dst — переводим в обратную сторону:
    между en↔ru инвертируем внутри пары, для остальных случаев dst=en
    (либо dst=ru, если preferred уже был en).
    """
    src = detect_source(text)
    if src != preferred_dst:
        return src, preferred_dst
    # Совпадение src и preferred_dst — нужен fallback-dst.
    if preferred_dst == "en":
        return src, "ru"
    return src, "en"


LANG_LABELS: dict[str, str] = {code: code.upper() for code, _ in POPULAR_LANGUAGES}


def language_name(code: str) -> str:
    for c, name in POPULAR_LANGUAGES:
        if c == code:
            return name
    return code


def direction_label(src: str, dst: str) -> str:
    return f"{LANG_LABELS.get(src, src.upper())} → {LANG_LABELS.get(dst, dst.upper())}"


def normalize_lang_code(code: str | None, fallback: str = "en") -> str:
    if not code:
        return fallback
    code = code.strip().lower()
    if code in LANGUAGE_CODES:
        return code
    return fallback
