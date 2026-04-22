from __future__ import annotations

from typing import Any

SUPPORTED_UI_LANGS: list[tuple[str, str]] = [
    ("ru", "Русский"),
    ("en", "English"),
]

DEFAULT_UI_LANG = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        # Трей
        "tray.pause": "Пауза",
        "tray.resume": "Продолжить",
        "tray.editor": "Режим редактора",
        "tray.settings": "Настройки…",
        "tray.quit": "Выход",
        "tray.provider_line": "Провайдер: {name}  [{mark}]",
        "tray.provider_ok": "✓",
        "tray.provider_no_key": "⚠ без ключа",
        "tray.tooltip": "translato — {name}",
        "tray.tooltip_paused_suffix": " — пауза",
        "tray.unavailable": "Системный трей недоступен в этой системе.",
        # Уведомления
        "notify.missing_key_openrouter": "API-ключ OpenRouter не задан. Откройте «Настройки» в трее.",
        "notify.missing_key_anthropic": "API-ключ Anthropic не задан. Откройте «Настройки» в трее.",
        # Popup
        "popup.translating": "Переводится…",
        "popup.updating": "Обновляется…",
        "popup.copy": "Скопировать",
        "popup.copied": "Скопировано",
        "popup.edit": "Редактор",
        "popup.src_tooltip": "Язык оригинала",
        "popup.dst_tooltip": "Язык перевода",
        "popup.resize_tooltip": "Потяни, чтобы изменить размер",
        # Editor
        "editor.title": "translato — редактор",
        "editor.source_placeholder": "Введите текст для перевода…",
        "editor.translation_placeholder": "Перевод появится здесь",
        "editor.swap_tooltip": "Поменять языки местами",
        "editor.translating": "Переводится…",
        "editor.ready": "Готово",
        # Диалог настроек
        "settings.title": "Настройки translato",
        "settings.tab_provider": "Провайдер",
        "settings.tab_instruction": "Инструкция",
        "settings.tab_languages": "Языки",
        "settings.provider_label": "Провайдер:",
        "settings.active_now": "Сейчас используется: <b>{name}</b>",
        "settings.will_switch": "Сейчас используется: <b>{current}</b>. После «OK» переключится на <b>{next}</b>.",
        "settings.provider_hint": (
            "Выбранный в списке провайдер становится активным после нажатия «OK». "
            "Ключи для обоих провайдеров хранятся независимо, можно держать оба."
        ),
        "settings.model_label": "Модель:",
        "settings.new_key_label": "Новый ключ:",
        "settings.delete_key_btn": "Удалить сохранённый ключ",
        "settings.key_saved": '<span style="color:#2e7d32;">● Ключ сохранён:</span> <code>{mask}</code>',
        "settings.key_missing": '<span style="color:#c62828;">● Ключ не задан</span>',
        "settings.key_replace_placeholder": "(введите, чтобы заменить сохранённый ключ)",
        "settings.confirm_delete_key": "Удалить сохранённый ключ {provider} из Windows Credential Manager?",
        "settings.link_openrouter": 'Ключ OpenRouter: <a href="https://openrouter.ai/keys">openrouter.ai/keys</a>',
        "settings.link_anthropic": (
            'Ключ Anthropic: <a href="https://console.anthropic.com/settings/keys">'
            'console.anthropic.com/settings/keys</a>'
        ),
        "settings.instruction_title": "Дополнительная инструкция для модели:",
        "settings.instruction_placeholder": (
            "Добавляется поверх основного промпта, не заменяет его.\n"
            "Например: «Используй формальный стиль» или «Термины из IT оставляй по-английски»."
        ),
        "settings.instruction_hint": (
            "Инструкция применяется поверх системного промпта переводчика "
            "и не может его переопределить. Работает для обоих провайдеров."
        ),
        "settings.translation_lang_title": "Язык перевода по умолчанию:",
        "settings.translation_lang_hint": (
            "Этот язык будет использоваться как целевой при переводе. "
            "Если исходный текст уже на этом языке, перевод пойдёт в обратную сторону "
            "(между русским и английским). В окне перевода язык можно быстро сменить "
            "в выпадающем списке."
        ),
        "settings.ui_lang_title": "Язык интерфейса:",
        "settings.ui_lang_hint": (
            "Язык самого приложения: меню трея, окно настроек, подсказки. "
            "После изменения достаточно переоткрыть окно настроек."
        ),
        # Ошибки провайдеров
        "err.openai_pkg_missing": "Пакет openai не установлен: {e}",
        "err.anthropic_pkg_missing": "Пакет anthropic не установлен: {e}. Установите: pip install anthropic",
        "err.anthropic_pkg_missing_short": "Пакет anthropic не установлен: {e}",
        "err.key_missing_openrouter": "API-ключ OpenRouter не задан. Откройте «Настройки» в трее.",
        "err.key_missing_anthropic": "API-ключ Anthropic не задан. Откройте «Настройки» в трее.",
        "err.key_non_ascii_openrouter": (
            "В сохранённом ключе есть не-ASCII символы. "
            "Скопируйте ключ заново со страницы openrouter.ai/keys "
            "и вставьте его через «Настройки»."
        ),
        "err.key_non_ascii_anthropic": (
            "В сохранённом ключе есть не-ASCII символы. "
            "Скопируйте ключ заново с console.anthropic.com "
            "и вставьте его через «Настройки»."
        ),
        "err.invalid_key_openrouter": "Недействительный API-ключ. Введите ключ заново в «Настройках».",
        "err.invalid_key_anthropic": "Недействительный API-ключ Anthropic. Введите ключ заново в «Настройках».",
        "err.rate_limit_openrouter": "Превышен лимит запросов OpenRouter. Попробуйте позже.",
        "err.rate_limit_anthropic": "Превышен лимит запросов Anthropic. Попробуйте позже.",
        "err.no_connection_openrouter": "Нет соединения с OpenRouter. Проверьте интернет.",
        "err.no_connection_anthropic": "Нет соединения с Anthropic. Проверьте интернет.",
        "err.api_generic": "Ошибка API (код {status}).",
        "err.api_anthropic": "Ошибка API Anthropic (код {status}).",
        "err.translation_generic": "Сбой перевода: {e}",
        "err.empty_response": "Пустой ответ от модели.",
        "err.refusal": (
            "Модель отказалась переводить этот фрагмент. "
            "Попробуйте ещё раз или немного измените текст."
        ),
        "err.key_non_ascii_chars": (
            "Ключ содержит не-ASCII символы в позициях {bad}. "
            "Скорее всего при вставке попала буква в другой кодировке. "
            "Скопируйте ключ заново с сайта провайдера."
        ),
    },
    "en": {
        # Tray
        "tray.pause": "Pause",
        "tray.resume": "Resume",
        "tray.editor": "Edit mode",
        "tray.settings": "Settings…",
        "tray.quit": "Quit",
        "tray.provider_line": "Provider: {name}  [{mark}]",
        "tray.provider_ok": "✓",
        "tray.provider_no_key": "⚠ no key",
        "tray.tooltip": "translato — {name}",
        "tray.tooltip_paused_suffix": " — paused",
        "tray.unavailable": "System tray is not available on this system.",
        # Notifications
        "notify.missing_key_openrouter": "OpenRouter API key is not set. Open “Settings” in the tray.",
        "notify.missing_key_anthropic": "Anthropic API key is not set. Open “Settings” in the tray.",
        # Popup
        "popup.translating": "Translating…",
        "popup.updating": "Updating…",
        "popup.copy": "Copy",
        "popup.copied": "Copied",
        "popup.edit": "Editor",
        "popup.src_tooltip": "Source language",
        "popup.dst_tooltip": "Target language",
        "popup.resize_tooltip": "Drag to resize",
        # Editor
        "editor.title": "translato — editor",
        "editor.source_placeholder": "Enter text to translate…",
        "editor.translation_placeholder": "Translation will appear here",
        "editor.swap_tooltip": "Swap languages",
        "editor.translating": "Translating…",
        "editor.ready": "Ready",
        # Settings dialog
        "settings.title": "translato Settings",
        "settings.tab_provider": "Provider",
        "settings.tab_instruction": "Instruction",
        "settings.tab_languages": "Languages",
        "settings.provider_label": "Provider:",
        "settings.active_now": "Currently used: <b>{name}</b>",
        "settings.will_switch": "Currently used: <b>{current}</b>. After “OK” will switch to <b>{next}</b>.",
        "settings.provider_hint": (
            "The provider selected in the list becomes active after clicking “OK”. "
            "Keys for both providers are stored independently — you can keep both."
        ),
        "settings.model_label": "Model:",
        "settings.new_key_label": "New key:",
        "settings.delete_key_btn": "Delete saved key",
        "settings.key_saved": '<span style="color:#2e7d32;">● Key saved:</span> <code>{mask}</code>',
        "settings.key_missing": '<span style="color:#c62828;">● Key not set</span>',
        "settings.key_replace_placeholder": "(type here to replace the saved key)",
        "settings.confirm_delete_key": "Delete the saved {provider} key from Windows Credential Manager?",
        "settings.link_openrouter": 'OpenRouter key: <a href="https://openrouter.ai/keys">openrouter.ai/keys</a>',
        "settings.link_anthropic": (
            'Anthropic key: <a href="https://console.anthropic.com/settings/keys">'
            'console.anthropic.com/settings/keys</a>'
        ),
        "settings.instruction_title": "Extra instruction for the model:",
        "settings.instruction_placeholder": (
            "Appended to the main prompt, does not replace it.\n"
            "E.g. “Use a formal tone” or “Keep IT terms in English”."
        ),
        "settings.instruction_hint": (
            "The instruction is applied on top of the translator's system prompt "
            "and cannot override it. Works for both providers."
        ),
        "settings.translation_lang_title": "Default target language:",
        "settings.translation_lang_hint": (
            "This language is used as the target for translation. "
            "If the source text is already in this language, translation flips direction "
            "(between Russian and English). You can quickly change the language "
            "in the dropdown inside the translation popup."
        ),
        "settings.ui_lang_title": "Interface language:",
        "settings.ui_lang_hint": (
            "Language of the app itself: tray menu, settings window, tooltips. "
            "After changing it, just reopen the Settings window."
        ),
        # Provider errors
        "err.openai_pkg_missing": "openai package is not installed: {e}",
        "err.anthropic_pkg_missing": "anthropic package is not installed: {e}. Install: pip install anthropic",
        "err.anthropic_pkg_missing_short": "anthropic package is not installed: {e}",
        "err.key_missing_openrouter": "OpenRouter API key is not set. Open “Settings” in the tray.",
        "err.key_missing_anthropic": "Anthropic API key is not set. Open “Settings” in the tray.",
        "err.key_non_ascii_openrouter": (
            "The saved key contains non-ASCII characters. "
            "Copy the key again from openrouter.ai/keys "
            "and paste it via “Settings”."
        ),
        "err.key_non_ascii_anthropic": (
            "The saved key contains non-ASCII characters. "
            "Copy the key again from console.anthropic.com "
            "and paste it via “Settings”."
        ),
        "err.invalid_key_openrouter": "Invalid API key. Enter the key again in “Settings”.",
        "err.invalid_key_anthropic": "Invalid Anthropic API key. Enter the key again in “Settings”.",
        "err.rate_limit_openrouter": "OpenRouter rate limit exceeded. Try again later.",
        "err.rate_limit_anthropic": "Anthropic rate limit exceeded. Try again later.",
        "err.no_connection_openrouter": "No connection to OpenRouter. Check your internet.",
        "err.no_connection_anthropic": "No connection to Anthropic. Check your internet.",
        "err.api_generic": "API error (code {status}).",
        "err.api_anthropic": "Anthropic API error (code {status}).",
        "err.translation_generic": "Translation failed: {e}",
        "err.empty_response": "Empty response from the model.",
        "err.refusal": (
            "The model refused to translate this fragment. "
            "Try again or slightly modify the text."
        ),
        "err.key_non_ascii_chars": (
            "The key contains non-ASCII characters at positions {bad}. "
            "Most likely a character in a different encoding was pasted. "
            "Copy the key again from the provider's site."
        ),
    },
}

_current_lang: str = DEFAULT_UI_LANG


def set_ui_lang(code: str) -> None:
    global _current_lang
    _current_lang = normalize_ui_lang(code)


def get_ui_lang() -> str:
    return _current_lang


def normalize_ui_lang(code: str | None) -> str:
    if not code:
        return DEFAULT_UI_LANG
    c = code.strip().lower()
    if c in _STRINGS:
        return c
    return DEFAULT_UI_LANG


def t(key: str, **kwargs: Any) -> str:
    table = _STRINGS.get(_current_lang) or _STRINGS[DEFAULT_UI_LANG]
    template = table.get(key)
    if template is None:
        fallback = _STRINGS[DEFAULT_UI_LANG].get(key, key)
        template = fallback
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
