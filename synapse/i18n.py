from __future__ import annotations

from typing import Any

SUPPORTED_UI_LANGS: list[tuple[str, str]] = [
    ("ru", "Русский"),
    ("en", "English"),
    ("ja", "日本語"),
    ("es", "Español"),
    ("pt", "Português"),
]

DEFAULT_UI_LANG = "en"

_STRINGS: dict[str, dict[str, str]] = {
    "ru": {
        # Tray
        "tray.pause": "Пауза",
        "tray.resume": "Продолжить",
        "tray.editor": "Режим редактора",
        "tray.settings": "Настройки…",
        "tray.quit": "Выход",
        "tray.tooltip": "Synapse",
        "tray.tooltip_paused_suffix": " — пауза",
        "tray.unavailable": "Системный трей недоступен в этой системе.",
        # Notifications
        "notify.missing_key_openrouter": "API-ключ OpenRouter не задан. Откройте «Настройки» в трее.",
        "notify.missing_key_anthropic": "API-ключ Anthropic не задан. Откройте «Настройки» в трее.",
        # Popup
        "popup.translating": "Переводится…",
        "popup.updating": "Обновляется…",
        "popup.copy": "Скопировать",
        "popup.copied": "Скопировано",
        "popup.paste": "Вставить",
        "popup.pasted": "Вставлено",
        "popup.edit": "Редактор",
        "popup.src_tooltip": "Язык оригинала",
        "popup.dst_tooltip": "Язык перевода",
        "popup.resize_tooltip": "Потяни, чтобы изменить размер",
        # Editor
        "editor.title": "Synapse — редактор",
        "editor.source_placeholder": "Введите текст для перевода…",
        "editor.translation_placeholder": "Перевод появится здесь",
        "editor.swap_tooltip": "Поменять языки местами",
        "editor.translating": "Переводится…",
        "editor.ready": "Готово",
        # Settings dialog
        "settings.title": "Настройки Synapse",
        "settings.tab_provider": "Провайдер",
        "settings.tab_instruction": "Инструкция",
        "settings.tab_system": "Система",
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
            "Основной язык, на который переводится текст. "
            "Если исходный текст уже на нём, перевод пойдёт на язык оригинала. "
            "Сменить язык можно в выпадающем списке окна перевода."
        ),
        "settings.ui_lang_title": "Язык интерфейса:",
        "settings.ui_lang_hint": (
            "Язык самого приложения: меню трея, окно настроек, подсказки. "
            "После изменения достаточно переоткрыть окно настроек."
        ),
        "settings.autostart_title": "Запуск:",
        "settings.autostart_checkbox": "Запускать при старте Windows",
        "settings.autostart_hint": (
            "Добавляет Synapse в автозагрузку текущего пользователя "
            "(HKCU\\…\\Run). Права администратора не требуются."
        ),
        "settings.close_on_copy_title": "Поведение окна перевода:",
        "settings.close_on_copy_checkbox": "Закрывать окно при копировании",
        "settings.close_on_copy_hint": (
            "Если включено, маленький попап закрывается после нажатия «Скопировать», "
            "а фокус возвращается в окно, откуда был взят текст. "
            "В режиме редактора настройка не действует."
        ),
        # Provider errors
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
        "tray.tooltip": "Synapse",
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
        "popup.paste": "Paste",
        "popup.pasted": "Pasted",
        "popup.edit": "Editor",
        "popup.src_tooltip": "Source language",
        "popup.dst_tooltip": "Target language",
        "popup.resize_tooltip": "Drag to resize",
        # Editor
        "editor.title": "Synapse — editor",
        "editor.source_placeholder": "Enter text to translate…",
        "editor.translation_placeholder": "Translation will appear here",
        "editor.swap_tooltip": "Swap languages",
        "editor.translating": "Translating…",
        "editor.ready": "Ready",
        # Settings dialog
        "settings.title": "Synapse Settings",
        "settings.tab_provider": "Provider",
        "settings.tab_instruction": "Instruction",
        "settings.tab_system": "System",
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
            "The main language to translate into. "
            "If the source text is already in it, translation goes into the source language instead. "
            "You can change the language in the dropdown of the translation popup."
        ),
        "settings.ui_lang_title": "Interface language:",
        "settings.ui_lang_hint": (
            "Language of the app itself: tray menu, settings window, tooltips. "
            "After changing it, just reopen the Settings window."
        ),
        "settings.autostart_title": "Startup:",
        "settings.autostart_checkbox": "Launch on Windows startup",
        "settings.autostart_hint": (
            "Adds Synapse to the current user's autostart "
            "(HKCU\\…\\Run). No administrator rights required."
        ),
        "settings.close_on_copy_title": "Translation window behavior:",
        "settings.close_on_copy_checkbox": "Close window on copy",
        "settings.close_on_copy_hint": (
            "If enabled, the small popup closes after clicking “Copy”, "
            "and focus returns to the window the text was taken from. "
            "Has no effect in editor mode."
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
    "ja": {
        # トレイ
        "tray.pause": "一時停止",
        "tray.resume": "再開",
        "tray.editor": "エディタモード",
        "tray.settings": "設定…",
        "tray.quit": "終了",
        "tray.tooltip": "Synapse",
        "tray.tooltip_paused_suffix": " — 一時停止中",
        "tray.unavailable": "このシステムではシステムトレイを利用できません。",
        # 通知
        "notify.missing_key_openrouter": "OpenRouter の API キーが設定されていません。トレイの「設定」を開いてください。",
        "notify.missing_key_anthropic": "Anthropic の API キーが設定されていません。トレイの「設定」を開いてください。",
        # ポップアップ
        "popup.translating": "翻訳中…",
        "popup.updating": "更新中…",
        "popup.copy": "コピー",
        "popup.copied": "コピーしました",
        "popup.paste": "貼り付け",
        "popup.pasted": "貼り付けました",
        "popup.edit": "エディタ",
        "popup.src_tooltip": "原文の言語",
        "popup.dst_tooltip": "翻訳先の言語",
        "popup.resize_tooltip": "ドラッグしてサイズを変更",
        # エディタ
        "editor.title": "Synapse — エディタ",
        "editor.source_placeholder": "翻訳するテキストを入力…",
        "editor.translation_placeholder": "翻訳結果はここに表示されます",
        "editor.swap_tooltip": "言語を入れ替える",
        "editor.translating": "翻訳中…",
        "editor.ready": "準備完了",
        # 設定ダイアログ
        "settings.title": "Synapse の設定",
        "settings.tab_provider": "プロバイダ",
        "settings.tab_instruction": "指示",
        "settings.tab_system": "システム",
        "settings.provider_label": "プロバイダ:",
        "settings.active_now": "現在の使用中: <b>{name}</b>",
        "settings.will_switch": "現在の使用中: <b>{current}</b>。「OK」を押すと <b>{next}</b> に切り替わります。",
        "settings.provider_hint": (
            "リストで選択したプロバイダは「OK」を押すと有効になります。"
            "両方のプロバイダのキーは別々に保存されるので、両方を保持できます。"
        ),
        "settings.model_label": "モデル:",
        "settings.new_key_label": "新しいキー:",
        "settings.delete_key_btn": "保存されたキーを削除",
        "settings.key_saved": '<span style="color:#2e7d32;">● キーを保存済み:</span> <code>{mask}</code>',
        "settings.key_missing": '<span style="color:#c62828;">● キーが未設定</span>',
        "settings.key_replace_placeholder": "(保存されたキーを置き換えるには入力してください)",
        "settings.confirm_delete_key": "Windows 資格情報マネージャーから保存された {provider} のキーを削除しますか?",
        "settings.link_openrouter": 'OpenRouter のキー: <a href="https://openrouter.ai/keys">openrouter.ai/keys</a>',
        "settings.link_anthropic": (
            'Anthropic のキー: <a href="https://console.anthropic.com/settings/keys">'
            'console.anthropic.com/settings/keys</a>'
        ),
        "settings.instruction_title": "モデルへの追加指示:",
        "settings.instruction_placeholder": (
            "メインのプロンプトに追加されます。置き換えはされません。\n"
            "例:「フォーマルな文体で」または「IT 用語は英語のままにする」。"
        ),
        "settings.instruction_hint": (
            "この指示は翻訳者のシステムプロンプトに上乗せされ、"
            "それを上書きすることはできません。両方のプロバイダで動作します。"
        ),
        "settings.translation_lang_title": "既定の翻訳先言語:",
        "settings.translation_lang_hint": (
            "テキストを翻訳するメイン言語です。"
            "原文がすでにこの言語の場合は、原文の言語へ翻訳されます。"
            "翻訳ポップアップのドロップダウンから言語を変更できます。"
        ),
        "settings.ui_lang_title": "インターフェース言語:",
        "settings.ui_lang_hint": (
            "アプリ自体の言語: トレイメニュー、設定画面、ツールチップ。"
            "変更後は設定ウィンドウを開き直すだけで反映されます。"
        ),
        "settings.autostart_title": "起動:",
        "settings.autostart_checkbox": "Windows 起動時に自動起動",
        "settings.autostart_hint": (
            "現在のユーザーの自動起動 (HKCU\\…\\Run) に Synapse を追加します。"
            "管理者権限は不要です。"
        ),
        "settings.close_on_copy_title": "翻訳ウィンドウの動作:",
        "settings.close_on_copy_checkbox": "コピー時にウィンドウを閉じる",
        "settings.close_on_copy_hint": (
            "有効にすると、「コピー」を押したあと小さなポップアップが閉じ、"
            "テキストを取得した元のウィンドウにフォーカスが戻ります。"
            "エディタモードでは適用されません。"
        ),
        # プロバイダのエラー
        "err.openai_pkg_missing": "openai パッケージがインストールされていません: {e}",
        "err.anthropic_pkg_missing": "anthropic パッケージがインストールされていません: {e}。インストール: pip install anthropic",
        "err.anthropic_pkg_missing_short": "anthropic パッケージがインストールされていません: {e}",
        "err.key_missing_openrouter": "OpenRouter の API キーが設定されていません。トレイの「設定」を開いてください。",
        "err.key_missing_anthropic": "Anthropic の API キーが設定されていません。トレイの「設定」を開いてください。",
        "err.key_non_ascii_openrouter": (
            "保存されたキーに非 ASCII 文字が含まれています。"
            "openrouter.ai/keys からキーをコピーし直し、"
            "「設定」から貼り付けてください。"
        ),
        "err.key_non_ascii_anthropic": (
            "保存されたキーに非 ASCII 文字が含まれています。"
            "console.anthropic.com からキーをコピーし直し、"
            "「設定」から貼り付けてください。"
        ),
        "err.invalid_key_openrouter": "無効な API キーです。「設定」でキーを再入力してください。",
        "err.invalid_key_anthropic": "無効な Anthropic API キーです。「設定」でキーを再入力してください。",
        "err.rate_limit_openrouter": "OpenRouter のリクエスト上限を超えました。後でもう一度お試しください。",
        "err.rate_limit_anthropic": "Anthropic のリクエスト上限を超えました。後でもう一度お試しください。",
        "err.no_connection_openrouter": "OpenRouter に接続できません。インターネット接続を確認してください。",
        "err.no_connection_anthropic": "Anthropic に接続できません。インターネット接続を確認してください。",
        "err.api_generic": "API エラー (コード {status})。",
        "err.api_anthropic": "Anthropic API エラー (コード {status})。",
        "err.translation_generic": "翻訳に失敗しました: {e}",
        "err.empty_response": "モデルからの応答が空です。",
        "err.refusal": (
            "モデルはこの断片の翻訳を拒否しました。"
            "もう一度試すか、テキストを少し修正してください。"
        ),
        "err.key_non_ascii_chars": (
            "キーの位置 {bad} に非 ASCII 文字が含まれています。"
            "貼り付け時に別のエンコーディングの文字が混入した可能性があります。"
            "プロバイダのサイトからキーをコピーし直してください。"
        ),
    },
    "es": {
        # Bandeja
        "tray.pause": "Pausar",
        "tray.resume": "Reanudar",
        "tray.editor": "Modo editor",
        "tray.settings": "Ajustes…",
        "tray.quit": "Salir",
        "tray.tooltip": "Synapse",
        "tray.tooltip_paused_suffix": " — en pausa",
        "tray.unavailable": "La bandeja del sistema no está disponible en este sistema.",
        # Notificaciones
        "notify.missing_key_openrouter": "La clave API de OpenRouter no está configurada. Abre «Ajustes» en la bandeja.",
        "notify.missing_key_anthropic": "La clave API de Anthropic no está configurada. Abre «Ajustes» en la bandeja.",
        # Popup
        "popup.translating": "Traduciendo…",
        "popup.updating": "Actualizando…",
        "popup.copy": "Copiar",
        "popup.copied": "Copiado",
        "popup.paste": "Pegar",
        "popup.pasted": "Pegado",
        "popup.edit": "Editor",
        "popup.src_tooltip": "Idioma de origen",
        "popup.dst_tooltip": "Idioma de destino",
        "popup.resize_tooltip": "Arrastra para cambiar el tamaño",
        # Editor
        "editor.title": "Synapse — editor",
        "editor.source_placeholder": "Introduce el texto a traducir…",
        "editor.translation_placeholder": "La traducción aparecerá aquí",
        "editor.swap_tooltip": "Intercambiar idiomas",
        "editor.translating": "Traduciendo…",
        "editor.ready": "Listo",
        # Diálogo de ajustes
        "settings.title": "Ajustes de Synapse",
        "settings.tab_provider": "Proveedor",
        "settings.tab_instruction": "Instrucción",
        "settings.tab_system": "Sistema",
        "settings.provider_label": "Proveedor:",
        "settings.active_now": "En uso actualmente: <b>{name}</b>",
        "settings.will_switch": "En uso actualmente: <b>{current}</b>. Tras pulsar «OK» se cambiará a <b>{next}</b>.",
        "settings.provider_hint": (
            "El proveedor seleccionado en la lista se activa al pulsar «OK». "
            "Las claves de ambos proveedores se guardan de forma independiente, puedes conservar las dos."
        ),
        "settings.model_label": "Modelo:",
        "settings.new_key_label": "Nueva clave:",
        "settings.delete_key_btn": "Eliminar la clave guardada",
        "settings.key_saved": '<span style="color:#2e7d32;">● Clave guardada:</span> <code>{mask}</code>',
        "settings.key_missing": '<span style="color:#c62828;">● Clave no configurada</span>',
        "settings.key_replace_placeholder": "(escribe aquí para reemplazar la clave guardada)",
        "settings.confirm_delete_key": "¿Eliminar la clave guardada de {provider} del Administrador de credenciales de Windows?",
        "settings.link_openrouter": 'Clave de OpenRouter: <a href="https://openrouter.ai/keys">openrouter.ai/keys</a>',
        "settings.link_anthropic": (
            'Clave de Anthropic: <a href="https://console.anthropic.com/settings/keys">'
            'console.anthropic.com/settings/keys</a>'
        ),
        "settings.instruction_title": "Instrucción adicional para el modelo:",
        "settings.instruction_placeholder": (
            "Se añade al prompt principal, no lo reemplaza.\n"
            "Por ejemplo: «Usa un tono formal» o «Mantén los términos de TI en inglés»."
        ),
        "settings.instruction_hint": (
            "La instrucción se aplica sobre el prompt del sistema del traductor "
            "y no puede anularlo. Funciona para ambos proveedores."
        ),
        "settings.translation_lang_title": "Idioma de destino predeterminado:",
        "settings.translation_lang_hint": (
            "Idioma principal al que se traduce el texto. "
            "Si el texto original ya está en él, la traducción irá al idioma de origen. "
            "Puedes cambiar el idioma en la lista desplegable de la ventana de traducción."
        ),
        "settings.ui_lang_title": "Idioma de la interfaz:",
        "settings.ui_lang_hint": (
            "Idioma de la propia aplicación: menú de la bandeja, ventana de ajustes, tooltips. "
            "Tras cambiarlo, basta con volver a abrir la ventana de ajustes."
        ),
        "settings.autostart_title": "Inicio:",
        "settings.autostart_checkbox": "Iniciar con Windows",
        "settings.autostart_hint": (
            "Añade Synapse al inicio del usuario actual "
            "(HKCU\\…\\Run). No requiere permisos de administrador."
        ),
        "settings.close_on_copy_title": "Comportamiento de la ventana de traducción:",
        "settings.close_on_copy_checkbox": "Cerrar la ventana al copiar",
        "settings.close_on_copy_hint": (
            "Si está activado, el popup pequeño se cierra tras pulsar «Copiar» "
            "y el foco vuelve a la ventana de la que se tomó el texto. "
            "No tiene efecto en el modo editor."
        ),
        # Errores de los proveedores
        "err.openai_pkg_missing": "El paquete openai no está instalado: {e}",
        "err.anthropic_pkg_missing": "El paquete anthropic no está instalado: {e}. Instálalo: pip install anthropic",
        "err.anthropic_pkg_missing_short": "El paquete anthropic no está instalado: {e}",
        "err.key_missing_openrouter": "La clave API de OpenRouter no está configurada. Abre «Ajustes» en la bandeja.",
        "err.key_missing_anthropic": "La clave API de Anthropic no está configurada. Abre «Ajustes» en la bandeja.",
        "err.key_non_ascii_openrouter": (
            "La clave guardada contiene caracteres no ASCII. "
            "Copia de nuevo la clave desde openrouter.ai/keys "
            "y pégala mediante «Ajustes»."
        ),
        "err.key_non_ascii_anthropic": (
            "La clave guardada contiene caracteres no ASCII. "
            "Copia de nuevo la clave desde console.anthropic.com "
            "y pégala mediante «Ajustes»."
        ),
        "err.invalid_key_openrouter": "Clave API no válida. Vuelve a introducirla en «Ajustes».",
        "err.invalid_key_anthropic": "Clave API de Anthropic no válida. Vuelve a introducirla en «Ajustes».",
        "err.rate_limit_openrouter": "Se ha superado el límite de solicitudes de OpenRouter. Inténtalo más tarde.",
        "err.rate_limit_anthropic": "Se ha superado el límite de solicitudes de Anthropic. Inténtalo más tarde.",
        "err.no_connection_openrouter": "Sin conexión con OpenRouter. Comprueba tu conexión a Internet.",
        "err.no_connection_anthropic": "Sin conexión con Anthropic. Comprueba tu conexión a Internet.",
        "err.api_generic": "Error de API (código {status}).",
        "err.api_anthropic": "Error de la API de Anthropic (código {status}).",
        "err.translation_generic": "Fallo al traducir: {e}",
        "err.empty_response": "Respuesta vacía del modelo.",
        "err.refusal": (
            "El modelo se negó a traducir este fragmento. "
            "Inténtalo de nuevo o modifica ligeramente el texto."
        ),
        "err.key_non_ascii_chars": (
            "La clave contiene caracteres no ASCII en las posiciones {bad}. "
            "Lo más probable es que al pegar se colara un carácter de otra codificación. "
            "Copia de nuevo la clave desde el sitio del proveedor."
        ),
    },
    "pt": {
        # Bandeja
        "tray.pause": "Pausar",
        "tray.resume": "Retomar",
        "tray.editor": "Modo editor",
        "tray.settings": "Configurações…",
        "tray.quit": "Sair",
        "tray.tooltip": "Synapse",
        "tray.tooltip_paused_suffix": " — em pausa",
        "tray.unavailable": "A bandeja do sistema não está disponível neste sistema.",
        # Notificações
        "notify.missing_key_openrouter": "A chave da API do OpenRouter não está definida. Abra «Configurações» na bandeja.",
        "notify.missing_key_anthropic": "A chave da API da Anthropic não está definida. Abra «Configurações» na bandeja.",
        # Popup
        "popup.translating": "Traduzindo…",
        "popup.updating": "Atualizando…",
        "popup.copy": "Copiar",
        "popup.copied": "Copiado",
        "popup.paste": "Colar",
        "popup.pasted": "Colado",
        "popup.edit": "Editor",
        "popup.src_tooltip": "Idioma de origem",
        "popup.dst_tooltip": "Idioma de destino",
        "popup.resize_tooltip": "Arraste para redimensionar",
        # Editor
        "editor.title": "Synapse — editor",
        "editor.source_placeholder": "Digite o texto para traduzir…",
        "editor.translation_placeholder": "A tradução aparecerá aqui",
        "editor.swap_tooltip": "Trocar idiomas",
        "editor.translating": "Traduzindo…",
        "editor.ready": "Pronto",
        # Diálogo de configurações
        "settings.title": "Configurações do Synapse",
        "settings.tab_provider": "Provedor",
        "settings.tab_instruction": "Instrução",
        "settings.tab_system": "Sistema",
        "settings.provider_label": "Provedor:",
        "settings.active_now": "Em uso no momento: <b>{name}</b>",
        "settings.will_switch": "Em uso no momento: <b>{current}</b>. Após «OK» mudará para <b>{next}</b>.",
        "settings.provider_hint": (
            "O provedor selecionado na lista é ativado ao clicar em «OK». "
            "As chaves de ambos os provedores são armazenadas de forma independente, você pode manter as duas."
        ),
        "settings.model_label": "Modelo:",
        "settings.new_key_label": "Nova chave:",
        "settings.delete_key_btn": "Excluir chave salva",
        "settings.key_saved": '<span style="color:#2e7d32;">● Chave salva:</span> <code>{mask}</code>',
        "settings.key_missing": '<span style="color:#c62828;">● Chave não definida</span>',
        "settings.key_replace_placeholder": "(digite aqui para substituir a chave salva)",
        "settings.confirm_delete_key": "Excluir a chave salva de {provider} do Gerenciador de Credenciais do Windows?",
        "settings.link_openrouter": 'Chave do OpenRouter: <a href="https://openrouter.ai/keys">openrouter.ai/keys</a>',
        "settings.link_anthropic": (
            'Chave da Anthropic: <a href="https://console.anthropic.com/settings/keys">'
            'console.anthropic.com/settings/keys</a>'
        ),
        "settings.instruction_title": "Instrução adicional para o modelo:",
        "settings.instruction_placeholder": (
            "Adicionada ao prompt principal, não o substitui.\n"
            "Por exemplo: «Use um tom formal» ou «Mantenha os termos de TI em inglês»."
        ),
        "settings.instruction_hint": (
            "A instrução é aplicada sobre o prompt de sistema do tradutor "
            "e não pode sobrescrevê-lo. Funciona para ambos os provedores."
        ),
        "settings.translation_lang_title": "Idioma de destino padrão:",
        "settings.translation_lang_hint": (
            "Idioma principal para o qual o texto é traduzido. "
            "Se o texto original já estiver nele, a tradução vai para o idioma de origem. "
            "Você pode mudar o idioma na lista suspensa da janela de tradução."
        ),
        "settings.ui_lang_title": "Idioma da interface:",
        "settings.ui_lang_hint": (
            "Idioma do próprio aplicativo: menu da bandeja, janela de configurações, dicas. "
            "Após alterar, basta reabrir a janela de configurações."
        ),
        "settings.autostart_title": "Inicialização:",
        "settings.autostart_checkbox": "Iniciar com o Windows",
        "settings.autostart_hint": (
            "Adiciona o Synapse à inicialização do usuário atual "
            "(HKCU\\…\\Run). Não requer privilégios de administrador."
        ),
        "settings.close_on_copy_title": "Comportamento da janela de tradução:",
        "settings.close_on_copy_checkbox": "Fechar a janela ao copiar",
        "settings.close_on_copy_hint": (
            "Se ativado, o popup pequeno fecha após clicar em «Copiar» "
            "e o foco volta para a janela de onde o texto foi retirado. "
            "Não tem efeito no modo editor."
        ),
        # Erros dos provedores
        "err.openai_pkg_missing": "O pacote openai não está instalado: {e}",
        "err.anthropic_pkg_missing": "O pacote anthropic não está instalado: {e}. Instale: pip install anthropic",
        "err.anthropic_pkg_missing_short": "O pacote anthropic não está instalado: {e}",
        "err.key_missing_openrouter": "A chave da API do OpenRouter não está definida. Abra «Configurações» na bandeja.",
        "err.key_missing_anthropic": "A chave da API da Anthropic não está definida. Abra «Configurações» na bandeja.",
        "err.key_non_ascii_openrouter": (
            "A chave salva contém caracteres não ASCII. "
            "Copie a chave novamente em openrouter.ai/keys "
            "e cole-a via «Configurações»."
        ),
        "err.key_non_ascii_anthropic": (
            "A chave salva contém caracteres não ASCII. "
            "Copie a chave novamente em console.anthropic.com "
            "e cole-a via «Configurações»."
        ),
        "err.invalid_key_openrouter": "Chave de API inválida. Digite a chave novamente em «Configurações».",
        "err.invalid_key_anthropic": "Chave de API da Anthropic inválida. Digite a chave novamente em «Configurações».",
        "err.rate_limit_openrouter": "Limite de requisições do OpenRouter excedido. Tente novamente mais tarde.",
        "err.rate_limit_anthropic": "Limite de requisições da Anthropic excedido. Tente novamente mais tarde.",
        "err.no_connection_openrouter": "Sem conexão com o OpenRouter. Verifique sua internet.",
        "err.no_connection_anthropic": "Sem conexão com a Anthropic. Verifique sua internet.",
        "err.api_generic": "Erro da API (código {status}).",
        "err.api_anthropic": "Erro da API da Anthropic (código {status}).",
        "err.translation_generic": "Falha na tradução: {e}",
        "err.empty_response": "Resposta vazia do modelo.",
        "err.refusal": (
            "O modelo recusou-se a traduzir este trecho. "
            "Tente novamente ou altere ligeiramente o texto."
        ),
        "err.key_non_ascii_chars": (
            "A chave contém caracteres não ASCII nas posições {bad}. "
            "Provavelmente, ao colar, entrou um caractere de outra codificação. "
            "Copie a chave novamente no site do provedor."
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
