from __future__ import annotations

import sys
import traceback

import pyperclip
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from .config import debug_enabled, load_config, save_config
from .lang import detect_direction, direction_label
from .popup import PopupWindow
from .providers.base import TranslationError
from .providers.openrouter import OpenRouterTranslator, get_api_key
from .tray import TrayController, make_tray_icon


def _dbg(*a) -> None:
    if debug_enabled():
        print("[translato]", *a, file=sys.stderr)


class TranslationSignals(QObject):
    success = Signal(int, str)  # (request_id, translation)
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
            result = self._translator.translate(self._text, self._src, self._dst)
            self._signals.success.emit(self._id, result)
        except TranslationError as e:
            self._signals.failure.emit(self._id, str(e), e.kind)
        except Exception as e:
            _dbg("unexpected error:", traceback.format_exc())
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
        self._signals.success.connect(self._on_translation_success)
        self._signals.failure.connect(self._on_translation_failure)

        self._request_counter = 0
        self._paused = False

        popup_cfg = self._cfg.get("popup", {})
        self._popup = PopupWindow(
            default_width=int(popup_cfg.get("default_width", popup_cfg.get("max_width", 320))),
            cursor_offset_x=int(popup_cfg.get("cursor_offset_x", 16)),
            cursor_offset_y=int(popup_cfg.get("cursor_offset_y", 16)),
        )

        self._tray = TrayController(
            icon=make_tray_icon(),
            get_model=lambda: self._cfg["openrouter"]["model"],
            set_model=self._set_model,
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

    def _set_model(self, model: str) -> None:
        self._cfg["openrouter"]["model"] = model
        save_config(self._cfg)

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
        except Exception as e:
            _dbg("clipboard error:", e)
            return
        if not text or not text.strip():
            return

        src, dst = detect_direction(text)
        api_key = get_api_key()
        if not api_key:
            self._popup.show_loading(direction_label(src, dst))
            self._popup.show_error(
                "API-ключ OpenRouter не задан. Откройте «Настройки» в трее."
            )
            return

        self._popup.show_loading(direction_label(src, dst))

        self._request_counter += 1
        request_id = self._request_counter

        translator = OpenRouterTranslator(
            model=self._cfg["openrouter"]["model"],
            base_url=self._cfg["openrouter"]["base_url"],
        )
        job = TranslationJob(translator, text, src, dst, request_id, self._signals)
        self._pool.start(job)

    @Slot(int, str)
    def _on_translation_success(self, request_id: int, translation: str) -> None:
        if request_id != self._request_counter:
            return  # устарело, уже есть новый запрос
        self._popup.show_translation(translation)

    @Slot(int, str, str)
    def _on_translation_failure(self, request_id: int, message: str, kind: str) -> None:
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


def _ensure_api_key_on_startup(tray: TrayController) -> None:
    if get_api_key():
        return
    tray.notify(
        "translato",
        "Не задан API-ключ OpenRouter. Откройте «Настройки» в трее.",
    )


def main() -> int:
    qapp = QApplication.instance() or QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setApplicationName("translato")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        TrayController.warn_missing_tray()
        return 2

    app = TranslatoApp(qapp)
    _ensure_api_key_on_startup(app._tray)

    return qapp.exec()


if __name__ == "__main__":
    raise SystemExit(main())
