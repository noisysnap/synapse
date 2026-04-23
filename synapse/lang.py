from __future__ import annotations

import re

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


_CYRILLIC = "cyr"  # внутренний маркер, уточняется через _cyrillic_hint


# Уникальные буквы украинского, которых нет в русском.
_UK_LETTERS = set("іїєґІЇЄҐ")
# Уникальные буквы русского, которых нет в украинском.
_RU_LETTERS = set("ыъэёЫЪЭЁ")


def _script_of(ch: str) -> str | None:
    """Вернуть код языка по Unicode-блоку одиночного символа, если он
    однозначно ассоциируется с языком. Для латиницы возвращает None —
    различить, скажем, English и French по буквам без словаря нельзя.

    Для кириллицы возвращает маркер _CYRILLIC — разделение ru/uk делается
    отдельно в _cyrillic_hint по уникальным буквам каждого алфавита."""
    cp = ord(ch)
    # Кириллица: основной блок + доп. расширения (в т.ч. украинские буквы).
    if 0x0400 <= cp <= 0x04FF or 0x0500 <= cp <= 0x052F:
        return _CYRILLIC
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
    # Арабский: основной блок, дополнение, Extended-A, Presentation Forms A/B.
    if (0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F
            or 0x08A0 <= cp <= 0x08FF
            or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF):
        return "ar"
    # Тайский.
    if 0x0E00 <= cp <= 0x0E7F:
        return "th"
    # Деванагари (хинди).
    if 0x0900 <= cp <= 0x097F:
        return "hi"
    return None


def _cyrillic_hint(text: str) -> str:
    """Разделить ru и uk по уникальным буквам и стоп-словам.

    Украинский имеет і/ї/є/ґ (отсутствуют в русском), русский — ы/ъ/э/ё
    (отсутствуют в украинском). Если букв-маркеров нет (короткий текст,
    совпадающий с обоими алфавитами), пробуем матч по стоп-словам; иначе
    дефолтимся в ru."""
    has_uk = any(ch in _UK_LETTERS for ch in text)
    has_ru = any(ch in _RU_LETTERS for ch in text)
    if has_uk and not has_ru:
        return "uk"
    if has_ru and not has_uk:
        return "ru"
    # Нет явных маркеров (например, чисто общие буквы или очень короткий
    # текст) — пробуем стоп-слова.
    hint = _stopword_hint(text, allowed={"ru", "uk"})
    return hint or "ru"


# Характерные диакритические буквы по языкам. В отличие от unique-наборов
# буквы здесь могут пересекаться между языками (например, ü есть и в de, и в
# tr, и в sv) — финальный выбор делает score-агрегация в _latin_hint с учётом
# стоп-слов. Включать сюда нужно только буквы, которые реально поднимают
# сигнал именно для этого языка.
#
# Вьетнамский отдельно — у него блок Latin Extended Additional (U+1E00–U+1EFF),
# в котором буквы не встречаются ни в одном другом популярном языке.
_VI_UNIQUE = set("ơƠưƯđĐ")  # ă/ê/ô/â есть в других языках (ro, pt, fr), убраны
_DIACRITIC_MARKERS: dict[str, set[str]] = {
    "pl": set("łŁąĄęĘśŚćĆńŃźŹżŻ"),  # только польские — в других не встречаются
    "cs": set("řŘůŮěĚ"),              # чисто чешские
    "tr": set("ğĞıİçÇşŞ"),            # ğ/ı уникальны, ç/ş shared с pt/ro
    "de": set("ßẞäÄöÖüÜ"),            # ß уникальна, ä/ö/ü shared с tr/sv/hu
    "es": set("ñÑ¿¡áÁíÍóÓúÚéÉ"),      # ñ/¿/¡ уникальны, остальные shared
    "fr": set("çÇàÀâÂéÉèÈêÊëËîÎïÏôÔùÙûÛüÜÿŸœŒæÆ"),
    "it": set("àÀèÈéÉìÌíÍîÎòÒóÓùÙ"),
    "pt": set("ãÃõÕáÁâÂéÉêÊíÍóÓôÔúÚçÇ"),
    "nl": set("ëËïÏ"),                # диерезисы заметный сигнал для nl
    "sv": set("åÅäÄöÖ"),              # å уникальна, ä/ö shared с de
}
# Буквы, которые по-настоящему уникальны для одного языка среди популярных.
# Хоть одна встретилась — сразу решаем.
_DIACRITIC_EXCLUSIVE: dict[str, set[str]] = {
    "vi": _VI_UNIQUE,
    "pl": set("łŁąĄęĘśŚćĆńŃźŹżŻ"),
    "cs": set("řŘůŮěĚ"),
    "tr": set("ğĞıİ"),
    "de": set("ßẞ"),
    "es": set("ñÑ¿¡"),
    "sv": set("åÅ"),
    "pt": set("ãÃõÕ"),                # носовые тильды характерны для pt
    "fr": set("œŒæÆùÙÿŸ"),
}


# Частотные стоп-слова по языкам. Отобраны так, чтобы минимально пересекаться
# между языками — совпадение даже одного-двух слов даёт сильный сигнал.
# Используется для текстов без уникальной диакритики (например, чистый ASCII
# или пары слов вроде "the house" vs "la casa").
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
    # Русский и украинский добавлены только для fallback в _cyrillic_hint,
    # когда в тексте нет уникальных букв ни того, ни другого алфавита.
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

# Языки с латиницей для фильтра в _latin_hint, чтобы не сматчить случайно
# кириллические стоп-слова (они в _STOPWORDS ради fallback-а в _cyrillic_hint).
_LATIN_STOPWORD_LANGS = frozenset({
    "en", "es", "fr", "de", "it", "pt", "nl", "sv", "pl", "cs", "tr", "id", "vi",
})


def _stopword_hint(
    text: str,
    min_letters: int = 4,
    allowed: set[str] | frozenset[str] | None = None,
) -> str | None:
    """Посчитать попадания стоп-слов и выбрать язык-лидер.

    Возвращает код языка, если нашёлся явный лидер (минимум 2 попадания
    или значимый отрыв), иначе None. min_letters — минимум букв в тексте,
    чтобы вообще запускать подсчёт (на очень коротких строках результат
    ненадёжен). allowed — если задан, подсчёт ограничивается этими языками
    (используется, чтобы разделять только ru/uk внутри кириллицы и т.п.)."""
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
    # Требуем либо ≥2 попаданий (уверенный сигнал), либо отрыва от второго
    # места — иначе одиночное слово вроде "de" матчит сразу pt/es/nl.
    if best_score >= 2:
        return best_lang
    second = max((s for lang, s in scores.items() if lang != best_lang),
                 default=0)
    if best_score > second:
        return best_lang
    return None


def _latin_hint(text: str) -> str | None:
    """Определить латиноалфавитный язык по диакритикам и стоп-словам.

    Сначала проверяем эксклюзивные диакритики — если нашлась буква, которая
    встречается только в одном языке, этого достаточно. Иначе складываем
    очки от shared-диакритик и попаданий по стоп-словам и выбираем лидера."""
    # 1) Эксклюзивные маркеры: любая буква из Latin Extended Additional — vi.
    for ch in text:
        if 0x1E00 <= ord(ch) <= 0x1EFF:
            return "vi"
    # Прочие эксклюзивные диакритики (ł → pl, ř → cs, ğ → tr, ß → de, ñ → es,
    # å → sv, ã/õ → pt, œ/æ → fr, ơ/ư/đ → vi).
    for ch in text:
        for lang, chars in _DIACRITIC_EXCLUSIVE.items():
            if ch in chars:
                return lang
    # 2) Score-based: shared-диакритики + стоп-слова.
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
                # Стоп-слово весит больше диакритики: диакритик много в
                # каждом слове, а попадание в стоп-лист — более редкий и
                # более специфичный сигнал.
                scores[lang] = scores.get(lang, 0) + hits * 3
    if not scores:
        return None
    best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score >= 2:
        return best_lang
    return None


def detect_source(text: str) -> str:
    """Определить язык оригинала по скриптам Юникода.

    Для языков с уникальной письменностью (ja/ko/zh/ar/th/hi) возвращает
    конкретный код. Кириллицу разрешает в ru/uk по маркерным буквам и стоп-
    словам. Для латиницы пытается распознать по характерным диакритикам
    (vi/pl/cs/tr/de/es) и частотным стоп-словам (en/fr/it/pt/nl/sv/id) —
    иначе отдаёт 'en'. Пользователь всегда может исправить через src-combo."""
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
    # Японский приоритетнее китайского: если нашли хоть одну кану — это
    # точно японский, даже если ханьских иероглифов больше.
    if counts.get("ja", 0) > 0:
        return "ja"
    # Лидирующий по доле скрипт, но только если он занимает заметную часть
    # букв (>30%), иначе считаем текст латинским.
    best_lang, best_count = max(counts.items(), key=lambda kv: kv[1])
    if best_count / total_letters > 0.30:
        if best_lang == _CYRILLIC:
            return _cyrillic_hint(text)
        return best_lang
    hint = _latin_hint(text)
    return hint or "en"


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
