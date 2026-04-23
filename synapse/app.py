from __future__ import annotations

import sys

import pyperclip
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from . import autostart
from .config import load_config, save_config
from .editor import EditorWindow
from .i18n import normalize_ui_lang, set_ui_lang, t
from .lang import normalize_lang_code, resolve_direction
from .popup import PopupWindow
from .providers.base import TranslationError
from .providers.openrouter import OpenRouterTranslator
from .providers.anthropic_direct import AnthropicTranslator
from .providers.keys import get_openrouter_key, get_anthropic_key
from .tray import TrayController, app_icon, make_tray_icon


class TranslationSignals(QObject):
    started = Signal(int)  # (request_id) — начался стрим
    delta = Signal(int, str)  # (request_id, chunk)
    finished = Signal(int)  # (request_id) — стрим завершён успешно
    failure = Signal(int, str, str)  # (request_id, message, kind)


class TranslationJob(QRunnable):
    def __init__(self, translator, text: str, src: str, dst: str,
                 request_id: int, signals: TranslationSignals) -> None:
        super().__init__()
        self._translator = translator
        self._text = text
        self._src = src
        self._dst = dst
        self._id = request_id
        self._signals = signals

    @Slot()
    def run(self) -> None:
        try:
            first = True
            for chunk in self._translator.translate_stream(self._text, self._src, self._dst):
                if first:
                    self._signals.started.emit(self._id)
                    first = False
                if chunk:
                    self._signals.delta.emit(self._id, chunk)
            if first:
                # Стрим не выдал ничего — это ошибка.
                self._signals.failure.emit(self._id, t("err.empty_response"), "generic")
                return
            self._signals.finished.emit(self._id)
        except TranslationError as e:
            self._signals.failure.emit(self._id, str(e), e.kind)
        except Exception as e:
            self._signals.failure.emit(self._id, t("err.translation_generic", e=e), "generic")


class TriggerBridge(QObject):
    """Проброс события из потока pynput в главный Qt-поток."""

    fired = Signal()


class SynapseApp(QObject):
    def __init__(self, qapp: QApplication) -> None:
        super().__init__()
        self._qapp = qapp
        self._cfg = load_config()
        set_ui_lang(normalize_ui_lang(self._cfg.get("ui_lang")))

        self._pool = QThreadPool.globalInstance()
        self._signals = TranslationSignals()
        self._signals.started.connect(self._on_translation_started)
        self._signals.delta.connect(self._on_translation_delta)
        self._signals.finished.connect(self._on_translation_finished)
        self._signals.failure.connect(self._on_translation_failure)

        self._request_counter = 0
        self._paused = False

        # Persistent translators — держим оба, создаём по требованию,
        # чтобы HTTP keep-alive не рвался между триггерами.
        self._openrouter: OpenRouterTranslator | None = None
        self._anthropic: AnthropicTranslator | None = None

        popup_cfg = self._cfg.get("popup", {})
        self._popup = PopupWindow(
            default_width=int(popup_cfg.get("default_width", popup_cfg.get("max_width", 480))),
            default_height=int(popup_cfg.get("default_height", 320)),
            cursor_offset_x=int(popup_cfg.get("cursor_offset_x", 16)),
            cursor_offset_y=int(popup_cfg.get("cursor_offset_y", 16)),
            preferred_dst=normalize_lang_code(self._cfg.get("preferred_dst_lang"), "en"),
            close_on_copy=bool(popup_cfg.get("close_on_copy", False)),
        )
        self._popup.dst_language_changed.connect(self._on_popup_dst_changed)
        self._popup.src_language_changed.connect(self._on_popup_src_changed)
        self._popup.edit_requested.connect(self._on_popup_edit_requested)
        self._last_source_text: str = ""
        self._current_src: str = "en"
        self._current_dst: str = normalize_lang_code(
            self._cfg.get("preferred_dst_lang"), "en"
        )
        self._soft_by_request: dict[int, bool] = {}
        # target для каждого request_id: "popup" или "editor"
        self._target_by_request: dict[int, str] = {}

        # Editor создаётся лениво при первом открытии.
        self._editor: EditorWindow | None = None
        self._editor_last_source: str = ""

        self._tray = TrayController(
            icon=make_tray_icon(),
            get_config=lambda: self._cfg,
            on_config_saved=self._on_config_saved,
            on_pause_toggled=self._on_pause_toggled,
            on_editor_requested=self._open_editor_empty,
            on_quit=self._quit,
        )

        self._bridge = TriggerBridge()
        self._bridge.fired.connect(self._handle_trigger)

        from .trigger import DoubleCtrlCTrigger
        self._trigger = DoubleCtrlCTrigger(
            on_trigger=self._bridge.fired.emit,
            window_ms=int(self._cfg.get("trigger", {}).get("double_c_window_ms", 400)),
        )
        self._trigger.start()

    # --- config helpers -----------------------------------------------------

    def _on_config_saved(self, cfg_updates: dict) -> None:
        """Принять обновления из диалога настроек, смерджить, сохранить.
        Также сбрасывает кэш translator'ов, если сменилась модель/URL."""
        prev_or_model = self._cfg["openrouter"]["model"]
        prev_or_url = self._cfg["openrouter"]["base_url"]
        prev_an_model = self._cfg["anthropic"]["model"]
        prev_prompt = self._cfg.get("custom_prompt", "")
        prev_ui_lang = normalize_ui_lang(self._cfg.get("ui_lang"))

        if "active_provider" in cfg_updates:
            self._cfg["active_provider"] = cfg_updates["active_provider"]
        if "custom_prompt" in cfg_updates:
            self._cfg["custom_prompt"] = cfg_updates["custom_prompt"]
        if "preferred_dst_lang" in cfg_updates:
            new_dst = normalize_lang_code(cfg_updates["preferred_dst_lang"], "en")
            self._cfg["preferred_dst_lang"] = new_dst
            self._popup.set_preferred_dst(new_dst)
        if "ui_lang" in cfg_updates:
            self._cfg["ui_lang"] = normalize_ui_lang(cfg_updates["ui_lang"])
        if "openrouter" in cfg_updates:
            self._cfg["openrouter"].update(cfg_updates["openrouter"])
        if "anthropic" in cfg_updates:
            self._cfg["anthropic"].update(cfg_updates["anthropic"])
        if "popup" in cfg_updates:
            self._cfg.setdefault("popup", {}).update(cfg_updates["popup"])
            if "close_on_copy" in cfg_updates["popup"]:
                self._popup.set_close_on_copy(bool(cfg_updates["popup"]["close_on_copy"]))

        new_ui_lang = normalize_ui_lang(self._cfg.get("ui_lang"))
        if new_ui_lang != prev_ui_lang:
            set_ui_lang(new_ui_lang)
            self._tray.apply_ui_language()
            self._popup.apply_ui_language()

        save_config(self._cfg)

        prompt_changed = self._cfg.get("custom_prompt", "") != prev_prompt
        if (self._cfg["openrouter"]["model"] != prev_or_model
                or self._cfg["openrouter"]["base_url"] != prev_or_url
                or prompt_changed):
            self._openrouter = None
        if self._cfg["anthropic"]["model"] != prev_an_model or prompt_changed:
            self._anthropic = None

    def _get_translator(self):
        provider = self._cfg.get("active_provider", "openrouter")
        custom_prompt = self._cfg.get("custom_prompt", "")
        if provider == "anthropic":
            if self._anthropic is None:
                self._anthropic = AnthropicTranslator(
                    model=self._cfg["anthropic"]["model"],
                    custom_prompt=custom_prompt,
                )
            return self._anthropic
        if self._openrouter is None:
            self._openrouter = OpenRouterTranslator(
                model=self._cfg["openrouter"]["model"],
                base_url=self._cfg["openrouter"]["base_url"],
                custom_prompt=custom_prompt,
            )
        return self._openrouter

    def _active_key_present(self) -> bool:
        provider = self._cfg.get("active_provider", "openrouter")
        if provider == "anthropic":
            return bool(get_anthropic_key())
        return bool(get_openrouter_key())

    def _active_missing_key_message(self) -> str:
        provider = self._cfg.get("active_provider", "openrouter")
        if provider == "anthropic":
            return t("notify.missing_key_anthropic")
        return t("notify.missing_key_openrouter")

    # --- trigger handling ---------------------------------------------------

    def _on_pause_toggled(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self._trigger.stop()
        else:
            self._trigger.start()

    @Slot()
    def _handle_trigger(self) -> None:
        if self._paused:
            return
        try:
            text = pyperclip.paste()
        except Exception:
            return
        if not text or not text.strip():
            return
        # Зафиксировать HWND исходного окна ДО показа попапа, чтобы потом
        # знать, куда возвращать фокус для Paste.
        self._popup.remember_source_window()
        self._last_source_text = text
        preferred_dst = normalize_lang_code(self._cfg.get("preferred_dst_lang"), "en")
        src, dst = resolve_direction(text, preferred_dst)
        self._current_src = src
        self._current_dst = dst
        self._run_translation(text, src, dst, soft=False)

    @Slot(str)
    def _on_popup_dst_changed(self, new_dst: str) -> None:
        """Пользователь сменил язык перевода прямо в popup — перевод обновляется
        без мигания «Переводится…», старый текст остаётся до первого чанка."""
        dst = normalize_lang_code(new_dst, "en")
        if not self._last_source_text or not self._last_source_text.strip():
            return
        # Пересчитываем src по тексту, чтобы обработать случай ru↔en инверсии
        # (если dst совпал с текущим src — направление переворачивается).
        src, dst = resolve_direction(self._last_source_text, dst)
        self._current_src = src
        self._current_dst = dst
        self._run_translation(self._last_source_text, src, dst, soft=True)

    @Slot(str)
    def _on_popup_src_changed(self, new_src: str) -> None:
        """Пользователь вручную сменил язык оригинала — используем его как есть,
        направление не пересчитываем."""
        src = normalize_lang_code(new_src, "en")
        if not self._last_source_text or not self._last_source_text.strip():
            return
        dst = self._current_dst
        if src == dst:
            # Нельзя переводить на тот же язык: инвертируем dst на разумный дефолт.
            dst = "ru" if src == "en" else "en"
        self._current_src = src
        self._current_dst = dst
        self._run_translation(self._last_source_text, src, dst, soft=True)

    def _run_translation(
        self, text: str, src: str, dst: str, *, soft: bool, target: str = "popup"
    ) -> None:
        if not self._active_key_present():
            if target == "editor" and self._editor is not None:
                self._editor.show_error(self._active_missing_key_message())
            else:
                self._popup.show_loading(src, dst)
                self._popup.show_error(self._active_missing_key_message())
            return

        if target == "popup":
            if soft:
                self._popup.set_direction(src, dst)
            else:
                self._popup.show_loading(src, dst)

        self._request_counter += 1
        request_id = self._request_counter
        self._soft_by_request[request_id] = soft
        self._target_by_request[request_id] = target

        translator = self._get_translator()
        job = TranslationJob(translator, text, src, dst, request_id, self._signals)
        self._pool.start(job)

    def _dispatch_target(self, request_id: int) -> str:
        return self._target_by_request.get(request_id, "popup")

    @Slot(int)
    def _on_translation_started(self, request_id: int) -> None:
        if request_id != self._request_counter:
            return
        target = self._dispatch_target(request_id)
        soft = self._soft_by_request.get(request_id, False)
        if target == "editor" and self._editor is not None:
            if soft:
                self._editor.begin_soft_replace()
            else:
                self._editor.begin_translation()
        else:
            if soft:
                self._popup.begin_soft_replace()
            else:
                self._popup.begin_translation()

    @Slot(int, str)
    def _on_translation_delta(self, request_id: int, chunk: str) -> None:
        if request_id != self._request_counter:
            return
        target = self._dispatch_target(request_id)
        if target == "editor" and self._editor is not None:
            self._editor.append_translation(chunk)
        else:
            self._popup.append_translation(chunk)

    @Slot(int)
    def _on_translation_finished(self, request_id: int) -> None:
        self._soft_by_request.pop(request_id, None)
        target = self._target_by_request.pop(request_id, "popup")
        if request_id != self._request_counter:
            return
        if target == "editor" and self._editor is not None:
            self._editor.finish_translation()
        else:
            self._popup.finish_translation()

    @Slot(int, str, str)
    def _on_translation_failure(self, request_id: int, message: str, kind: str) -> None:
        self._soft_by_request.pop(request_id, None)
        target = self._target_by_request.pop(request_id, "popup")
        if request_id != self._request_counter:
            return
        if target == "editor" and self._editor is not None:
            self._editor.show_error(message)
        else:
            self._popup.show_error(message)
        if kind == "auth":
            if self._tray.open_settings():
                pass  # пользователь мог ввести ключ; новый перевод он запустит сам

    # --- editor -------------------------------------------------------------

    def _ensure_editor(self) -> EditorWindow:
        if self._editor is not None:
            return self._editor
        ed_cfg = self._cfg.get("editor", {})
        preferred_dst = normalize_lang_code(self._cfg.get("preferred_dst_lang"), "en")
        # src по умолчанию — противоположный dst между ru/en, как и в popup.
        default_src = "ru" if preferred_dst == "en" else "en"
        self._editor = EditorWindow(
            default_width=int(ed_cfg.get("width", 900)),
            default_height=int(ed_cfg.get("height", 520)),
            debounce_ms=int(ed_cfg.get("debounce_ms", 500)),
            preferred_src=default_src,
            preferred_dst=preferred_dst,
        )
        self._editor.translate_requested.connect(self._on_editor_translate_requested)
        self._editor.closed.connect(self._on_editor_closed)
        return self._editor

    def _open_editor_empty(self) -> None:
        ed = self._ensure_editor()
        src = ed.current_src() or "en"
        dst = ed.current_dst() or normalize_lang_code(self._cfg.get("preferred_dst_lang"), "en")
        ed.show_empty(src, dst)

    @Slot()
    def _on_popup_edit_requested(self) -> None:
        ed = self._ensure_editor()
        src = self._current_src or "en"
        dst = self._current_dst or normalize_lang_code(self._cfg.get("preferred_dst_lang"), "en")
        ed.show_with(
            self._last_source_text,
            self._popup.current_translation(),
            src,
            dst,
        )

    @Slot(str, str, str)
    def _on_editor_translate_requested(self, text: str, src: str, dst: str) -> None:
        # Pause не глушит editor — это ручной ввод, а не clipboard-триггер.
        self._editor_last_source = text
        # soft=True, чтобы не мигало «Переводится…» при каждом нажатии,
        # но при первом запросе поле всё равно заполнится.
        self._run_translation(text, src, dst, soft=True, target="editor")

    @Slot()
    def _on_editor_closed(self) -> None:
        if self._editor is None:
            return
        size = self._editor.size()
        self._cfg.setdefault("editor", {})
        self._cfg["editor"]["width"] = int(size.width())
        self._cfg["editor"]["height"] = int(size.height())
        save_config(self._cfg)

    # --- lifecycle ----------------------------------------------------------

    def _quit(self) -> None:
        try:
            self._trigger.stop()
        except Exception:
            pass
        self._popup.hide()
        if self._editor is not None:
            self._editor.close()
        self._qapp.quit()


def _ensure_api_key_on_startup(app: "SynapseApp") -> None:
    if app._active_key_present():
        return
    app._tray.open_settings()


def main() -> int:
    qapp = QApplication.instance() or QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("synapse")
    qapp.setWindowIcon(app_icon())

    if not QSystemTrayIcon.isSystemTrayAvailable():
        TrayController.warn_missing_tray()
        return 2

    # Если пользователь перенёс папку со сборкой, записанная в реестре
    # команда автозапуска больше не ведёт к exe — перезаписываем.
    autostart.self_heal()

    app = SynapseApp(qapp)
    _ensure_api_key_on_startup(app)

    return qapp.exec()


if __name__ == "__main__":
    raise SystemExit(main())
