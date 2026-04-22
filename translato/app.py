from __future__ import annotations

import sys

import pyperclip
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .config import load_config, save_config
from .lang import normalize_lang_code, resolve_direction
from .popup import PopupWindow
from .providers.base import TranslationError
from .providers.openrouter import OpenRouterTranslator
from .providers.anthropic_direct import AnthropicTranslator
from .providers.keys import get_openrouter_key, get_anthropic_key
from .tray import TrayController, make_tray_icon


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
                self._signals.failure.emit(self._id, "Пустой ответ от модели.", "generic")
                return
            self._signals.finished.emit(self._id)
        except TranslationError as e:
            self._signals.failure.emit(self._id, str(e), e.kind)
        except Exception as e:
            self._signals.failure.emit(self._id, f"Сбой перевода: {e}", "generic")


class TriggerBridge(QObject):
    """Проброс события из потока pynput в главный Qt-поток."""

    fired = Signal()


class TranslatoApp(QObject):
    def __init__(self, qapp: QApplication) -> None:
        super().__init__()
        self._qapp = qapp
        self._cfg = load_config()

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
        )
        self._popup.dst_language_changed.connect(self._on_popup_dst_changed)
        self._popup.src_language_changed.connect(self._on_popup_src_changed)
        self._last_source_text: str = ""
        self._current_src: str = "en"
        self._current_dst: str = normalize_lang_code(
            self._cfg.get("preferred_dst_lang"), "en"
        )
        self._soft_by_request: dict[int, bool] = {}

        self._tray = TrayController(
            icon=make_tray_icon(),
            get_config=lambda: self._cfg,
            on_config_saved=self._on_config_saved,
            on_pause_toggled=self._on_pause_toggled,
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

        if "active_provider" in cfg_updates:
            self._cfg["active_provider"] = cfg_updates["active_provider"]
        if "custom_prompt" in cfg_updates:
            self._cfg["custom_prompt"] = cfg_updates["custom_prompt"]
        if "preferred_dst_lang" in cfg_updates:
            new_dst = normalize_lang_code(cfg_updates["preferred_dst_lang"], "en")
            self._cfg["preferred_dst_lang"] = new_dst
            self._popup.set_preferred_dst(new_dst)
        if "openrouter" in cfg_updates:
            self._cfg["openrouter"].update(cfg_updates["openrouter"])
        if "anthropic" in cfg_updates:
            self._cfg["anthropic"].update(cfg_updates["anthropic"])

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
            return "API-ключ Anthropic не задан. Откройте «Настройки» в трее."
        return "API-ключ OpenRouter не задан. Откройте «Настройки» в трее."

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

    def _run_translation(self, text: str, src: str, dst: str, *, soft: bool) -> None:
        if not self._active_key_present():
            self._popup.show_loading(src, dst)
            self._popup.show_error(self._active_missing_key_message())
            return

        if soft:
            self._popup.set_direction(src, dst)
        else:
            self._popup.show_loading(src, dst)

        self._request_counter += 1
        request_id = self._request_counter
        self._soft_by_request[request_id] = soft

        translator = self._get_translator()
        job = TranslationJob(translator, text, src, dst, request_id, self._signals)
        self._pool.start(job)

    @Slot(int)
    def _on_translation_started(self, request_id: int) -> None:
        if request_id != self._request_counter:
            return
        if self._soft_by_request.get(request_id, False):
            self._popup.begin_soft_replace()
        else:
            self._popup.begin_translation()

    @Slot(int, str)
    def _on_translation_delta(self, request_id: int, chunk: str) -> None:
        if request_id != self._request_counter:
            return
        self._popup.append_translation(chunk)

    @Slot(int)
    def _on_translation_finished(self, request_id: int) -> None:
        self._soft_by_request.pop(request_id, None)
        if request_id != self._request_counter:
            return
        self._popup.finish_translation()

    @Slot(int, str, str)
    def _on_translation_failure(self, request_id: int, message: str, kind: str) -> None:
        self._soft_by_request.pop(request_id, None)
        if request_id != self._request_counter:
            return
        self._popup.show_error(message)
        if kind == "auth":
            if self._tray.open_settings():
                pass  # пользователь мог ввести ключ; новый перевод он запустит сам

    # --- lifecycle ----------------------------------------------------------

    def _quit(self) -> None:
        try:
            self._trigger.stop()
        except Exception:
            pass
        self._popup.hide()
        self._qapp.quit()


def _ensure_api_key_on_startup(app: "TranslatoApp") -> None:
    if app._active_key_present():
        return
    app._tray.notify(
        "translato",
        app._active_missing_key_message(),
    )


def main() -> int:
    qapp = QApplication.instance() or QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("translato")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        TrayController.warn_missing_tray()
        return 2

    app = TranslatoApp(qapp)
    _ensure_api_key_on_startup(app)

    return qapp.exec()


if __name__ == "__main__":
    raise SystemExit(main())
