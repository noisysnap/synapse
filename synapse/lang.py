from __future__ import annotations

import re

# Popular translation languages. English is first (default).
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

# Human-friendly short labels shown in parentheses. Where the ISO language
# code differs from the conventional country/script abbreviation, we use the
# more familiar variant (JP for JA, KR for KO, CN for ZH, UA for UK).
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


_CYRILLIC = "cyr"  # internal marker, refined further by _cyrillic_hint


# Letters unique to Ukrainian (absent in Russian).
_UK_LETTERS = set("іїєґІЇЄҐ")
# Letters unique to Russian (absent in Ukrainian).
_RU_LETTERS = set("ыъэёЫЪЭЁ")


def _script_of(ch: str) -> str | None:
    """Return the language code for a single character based on its Unicode
    block, if it maps unambiguously to a language. For Latin letters returns
    None — without a dictionary you cannot tell, say, English from French by
    individual letters.

    For Cyrillic, returns the _CYRILLIC marker — splitting ru/uk happens
    separately in _cyrillic_hint via alphabet-specific letters."""
    cp = ord(ch)
    # Cyrillic: main block + supplementary extensions (incl. Ukrainian letters).
    if 0x0400 <= cp <= 0x04FF or 0x0500 <= cp <= 0x052F:
        return _CYRILLIC
    # Hiragana + Katakana → unambiguously Japanese.
    if 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
        return "ja"
    # Hangul.
    if (0xAC00 <= cp <= 0xD7AF) or (0x1100 <= cp <= 0x11FF) or (0x3130 <= cp <= 0x318F):
        return "ko"
    # CJK ideographs — assigned to Chinese (for purely ideographic text you
    # cannot distinguish Japanese from Chinese without a dictionary).
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
        return "zh"
    # Arabic: main block, supplement, Extended-A, Presentation Forms A/B.
    if (0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F
            or 0x08A0 <= cp <= 0x08FF
            or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF):
        return "ar"
    # Thai.
    if 0x0E00 <= cp <= 0x0E7F:
        return "th"
    # Devanagari (Hindi).
    if 0x0900 <= cp <= 0x097F:
        return "hi"
    return None


def _cyrillic_hint(text: str) -> str:
    """Split ru vs uk by unique letters and stop-words.

    Ukrainian has і/ї/є/ґ (absent in Russian); Russian has ы/ъ/э/ё (absent
    in Ukrainian). If neither marker is present (short text using only
    shared letters), try stop-words; otherwise default to ru."""
    has_uk = any(ch in _UK_LETTERS for ch in text)
    has_ru = any(ch in _RU_LETTERS for ch in text)
    if has_uk and not has_ru:
        return "uk"
    if has_ru and not has_uk:
        return "ru"
    # No clear markers (e.g. only shared letters or very short text) — try
    # stop-words.
    hint = _stopword_hint(text, allowed={"ru", "uk"})
    return hint or "ru"


# Characteristic diacritic letters by language. Unlike the unique sets,
# letters here can be shared between languages (e.g. ü appears in de, tr,
# and sv) — the final pick is the score aggregation in _latin_hint, which
# also considers stop-words. Only include letters that genuinely boost the
# signal for that specific language.
#
# Vietnamese is special — its Latin Extended Additional block
# (U+1E00–U+1EFF) contains letters not found in any other popular language.
_VI_UNIQUE = set("ơƠưƯđĐ")  # ă/ê/ô/â also appear in ro/pt/fr — excluded
_DIACRITIC_MARKERS: dict[str, set[str]] = {
    "pl": set("łŁąĄęĘśŚćĆńŃźŹżŻ"),  # Polish-only — not present elsewhere
    "cs": set("řŘůŮěĚ"),              # Czech-only
    "tr": set("ğĞıİçÇşŞ"),            # ğ/ı unique; ç/ş shared with pt/ro
    "de": set("ßẞäÄöÖüÜ"),            # ß unique; ä/ö/ü shared with tr/sv/hu
    "es": set("ñÑ¿¡áÁíÍóÓúÚéÉ"),      # ñ/¿/¡ unique; rest shared
    "fr": set("çÇàÀâÂéÉèÈêÊëËîÎïÏôÔùÙûÛüÜÿŸœŒæÆ"),
    "it": set("àÀèÈéÉìÌíÍîÎòÒóÓùÙ"),
    "pt": set("ãÃõÕáÁâÂéÉêÊíÍóÓôÔúÚçÇ"),
    "nl": set("ëËïÏ"),                # diaereses are a notable signal for nl
    "sv": set("åÅäÄöÖ"),              # å unique; ä/ö shared with de
}
# Letters truly unique to one language among the popular ones. A single
# match is enough to decide.
_DIACRITIC_EXCLUSIVE: dict[str, set[str]] = {
    "vi": _VI_UNIQUE,
    "pl": set("łŁąĄęĘśŚćĆńŃźŹżŻ"),
    "cs": set("řŘůŮěĚ"),
    "tr": set("ğĞıİ"),
    "de": set("ßẞ"),
    "es": set("ñÑ¿¡"),
    "sv": set("åÅ"),
    "pt": set("ãÃõÕ"),                # nasal tildes are characteristic of pt
    "fr": set("œŒæÆùÙÿŸ"),
}


# Frequent stop-words by language. Chosen to overlap minimally between
# languages — even one or two matches give a strong signal. Used for text
# without unique diacritics (e.g. plain ASCII, or pairs like "the house"
# vs "la casa").
_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset({
        "the", "and", "is", "are", "was", "were", "have", "has", "had",
        "this", "that", "with", "from", "which", "would", "could", "should",
        "about", "there", "their", "what", "when", "where", "been", "being",
        "you", "your", "for", "not", "but",
    }),
    "es": frozenset({
        "el", "la", "los", "las", "un", "una", "del", "por", "para", "con",
        "pero", "como", "más", "este", "esta", "estos", "estas", "porque",
        "cuando", "donde", "también", "muy", "eso", "esto", "ser", "está",
        "están", "hay", "son", "fue",
    }),
    "fr": frozenset({
        "le", "la", "les", "un", "une", "des", "du", "est", "sont", "dans",
        "pour", "avec", "pas", "mais", "sur", "par", "plus", "cette", "ces",
        "aussi", "être", "avoir", "fait", "tout", "tous", "nous", "vous",
        "ils", "elles", "comme", "très", "où",
    }),
    "de": frozenset({
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen",
        "und", "ist", "sind", "war", "waren", "nicht", "auch", "aber", "auf",
        "mit", "für", "von", "zu", "sich", "noch", "nur", "wie", "werden",
        "wird", "haben", "hat",
    }),
    "it": frozenset({
        "il", "lo", "la", "gli", "le", "un", "uno", "una", "del", "della",
        "dei", "degli", "delle", "che", "non", "per", "con", "più", "come",
        "sono", "stato", "essere", "anche", "quando", "dove", "questo",
        "questa", "questi", "queste",
    }),
    "pt": frozenset({
        "de", "do", "da", "dos", "das", "um", "uma", "para", "com", "não",
        "mais", "como", "mas", "está", "são", "foi", "ser", "também", "que",
        "por", "sobre", "muito", "isso", "isto", "porque", "quando", "onde",
        "você",
    }),
    "nl": frozenset({
        "de", "het", "een", "en", "is", "niet", "van", "dat", "die", "zijn",
        "maar", "ook", "voor", "met", "aan", "bij", "naar", "worden", "wordt",
        "heeft", "heb", "hebben", "zoals", "wanneer", "waar",
    }),
    "sv": frozenset({
        "och", "att", "det", "som", "en", "ett", "är", "var", "har", "hade",
        "inte", "med", "för", "till", "från", "också", "men", "eller", "när",
        "där", "vad", "sig", "blir", "blev",
    }),
    "pl": frozenset({
        "jest", "nie", "się", "że", "jak", "tak", "lub", "oraz", "który",
        "która", "które", "kiedy", "gdzie", "tylko", "także", "bardzo",
        "nawet", "jeszcze",
    }),
    "cs": frozenset({
        "je", "není", "byl", "byla", "bylo", "jsem", "jsi", "jsme", "jste",
        "jsou", "nebo", "také", "ale", "protože", "když", "kde", "jak", "tak",
        "velmi", "ještě", "který", "která", "které",
    }),
    "tr": frozenset({
        "bir", "bu", "şu", "ve", "ile", "için", "çok", "daha", "ama", "ancak",
        "gibi", "kadar", "sonra", "önce", "nasıl", "neden", "nerede", "ne",
        "değil", "olarak", "oldu",
    }),
    "id": frozenset({
        "yang", "dan", "di", "ke", "dari", "untuk", "dengan", "adalah",
        "tidak", "ini", "itu", "atau", "juga", "akan", "sudah", "bisa",
        "ada", "pada", "tapi", "karena", "jika", "ketika",
    }),
    "vi": frozenset({
        "và", "là", "của", "có", "không", "được", "cho", "với", "khi",
        "những", "này", "đó", "các", "để", "trong", "người", "một", "tôi",
        "bạn", "anh", "chị", "nhưng",
    }),
    # Russian and Ukrainian are included only as a fallback for
    # _cyrillic_hint when neither alphabet's unique letters appear.
    "ru": frozenset({
        "и", "в", "не", "на", "что", "с", "по", "это", "как", "а", "но",
        "он", "она", "они", "его", "её", "их", "был", "была", "было", "были",
        "есть", "для", "от", "же", "так", "только", "ещё", "уже", "очень",
        "потому", "если", "когда", "где",
    }),
    "uk": frozenset({
        "і", "в", "у", "не", "на", "що", "з", "по", "це", "як", "а", "але",
        "він", "вона", "вони", "його", "її", "їх", "був", "була", "було",
        "були", "для", "від", "же", "так", "тільки", "ще", "вже", "дуже",
        "тому", "якщо", "коли", "де",
    }),
}

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)

# Latin-script languages used as a filter in _latin_hint so we do not
# accidentally match Cyrillic stop-words (they live in _STOPWORDS for the
# _cyrillic_hint fallback).
_LATIN_STOPWORD_LANGS = frozenset({
    "en", "es", "fr", "de", "it", "pt", "nl", "sv", "pl", "cs", "tr", "id", "vi",
})


def _stopword_hint(
    text: str,
    min_letters: int = 4,
    allowed: set[str] | frozenset[str] | None = None,
) -> str | None:
    """Count stop-word hits and pick the leading language.

    Returns the language code when there is a clear leader (at least 2 hits
    or a meaningful gap), otherwise None. min_letters is the minimum letter
    count needed before running the count (the result is unreliable on very
    short strings). allowed, if set, restricts the count to those languages
    (used, e.g., to separate only ru/uk within Cyrillic)."""
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if len(words) < 2:
        return None
    letter_count = sum(len(w) for w in words)
    if letter_count < min_letters:
        return None
    word_set = set(words)
    scores: dict[str, int] = {}
    for lang, stops in _STOPWORDS.items():
        if allowed is not None and lang not in allowed:
            continue
        hits = len(word_set & stops)
        if hits:
            scores[lang] = hits
    if not scores:
        return None
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    # Require either ≥2 hits (a confident signal) or a gap over the runner-up,
    # otherwise a single word like "de" matches pt/es/nl all at once.
    if best_score >= 2:
        return best_lang
    second = max((s for lang, s in scores.items() if lang != best_lang),
                 default=0)
    if best_score > second:
        return best_lang
    return None


def _latin_hint(text: str) -> str | None:
    """Detect a Latin-script language by diacritics and stop-words.

    First we check exclusive diacritics — if any letter unique to a single
    language is present, that is enough. Otherwise we sum scores from shared
    diacritics and stop-word hits, and pick the leader."""
    # 1) Exclusive markers: any letter from Latin Extended Additional → vi.
    for ch in text:
        if 0x1E00 <= ord(ch) <= 0x1EFF:
            return "vi"
    # Other exclusive diacritics (ł → pl, ř → cs, ğ → tr, ß → de, ñ → es,
    # å → sv, ã/õ → pt, œ/æ → fr, ơ/ư/đ → vi).
    for ch in text:
        for lang, chars in _DIACRITIC_EXCLUSIVE.items():
            if ch in chars:
                return lang
    # 2) Score-based: shared diacritics + stop-words.
    scores: dict[str, int] = {}
    for ch in text:
        for lang, chars in _DIACRITIC_MARKERS.items():
            if ch in chars:
                scores[lang] = scores.get(lang, 0) + 1
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if len(words) >= 2:
        word_set = set(words)
        for lang in _LATIN_STOPWORD_LANGS:
            stops = _STOPWORDS.get(lang)
            if not stops:
                continue
            hits = len(word_set & stops)
            if hits:
                # A stop-word weighs more than a diacritic: diacritics
                # appear in many words, while landing in the stop-list is a
                # rarer and more specific signal.
                scores[lang] = scores.get(lang, 0) + hits * 3
    if not scores:
        return None
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score >= 2:
        return best_lang
    return None


def detect_source(text: str) -> str:
    """Detect the source language from Unicode scripts.

    Languages with unique scripts (ja/ko/zh/ar/th/hi) get a direct code.
    Cyrillic is resolved into ru/uk by marker letters and stop-words. For
    Latin scripts we try characteristic diacritics (vi/pl/cs/tr/de/es) and
    frequent stop-words (en/fr/it/pt/nl/sv/id) — otherwise return 'en'. The
    user can always override via the src combo."""
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
        hint = _latin_hint(text)
        return hint or "en"
    # Japanese takes priority over Chinese: if any kana is present it is
    # definitely Japanese, even if more Han ideographs are around.
    if counts.get("ja", 0) > 0:
        return "ja"
    # The leading script by share, but only if it covers a noticeable
    # fraction of letters (>30%); otherwise treat the text as Latin.
    best_lang, best_count = max(counts.items(), key=lambda kv: kv[1])
    if best_count / total_letters > 0.30:
        if best_lang == _CYRILLIC:
            return _cyrillic_hint(text)
        return best_lang
    hint = _latin_hint(text)
    return hint or "en"


def resolve_direction(text: str, preferred_dst: str) -> tuple[str, str]:
    """Compute the translation direction respecting the preferred language.

    If the source text is already in preferred_dst, translate the other way:
    for the en↔ru pair we invert inside the pair, otherwise dst=en (or
    dst=ru if preferred was already en).
    """
    src = detect_source(text)
    if src != preferred_dst:
        return src, preferred_dst
    # src equals preferred_dst — pick a fallback dst.
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
