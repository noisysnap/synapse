from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock

from pynput import keyboard

Callback = Callable[[], None]


class DoubleCtrlCTrigger:
    """Слушатель Ctrl+C+C.

    Срабатывает, когда при непрерывно зажатом Ctrl происходят два нажатия C
    (C↓ C↑ C↓) и второе C↓ попадает в окно double_c_window_ms после первого.
    Автоповторы от ОС (C↓ без промежуточного C↑) игнорируются. Любое
    отпускание Ctrl сбрасывает состояние.

    Слушатель не блокирует клавиши — первое Ctrl+C работает как обычно.
    """

    def __init__(self, on_trigger: Callback, window_ms: int = 400) -> None:
        self._on_trigger = on_trigger
        self._window = window_ms / 1000.0
        self._ctrl_down = False
        self._c_pressed_once = False  # было хотя бы одно завершённое нажатие C при зажатом Ctrl
        self._last_c_press_ts = 0.0
        self._c_is_down = False  # текущее физическое состояние клавиши C (для фильтра автоповтора)
        self._lock = Lock()
        self._listener: keyboard.Listener | None = None

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    @staticmethod
    def _is_ctrl(key) -> bool:
        return key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)

    @staticmethod
    def _is_c(key) -> bool:
        # При зажатом Ctrl pynput на Windows может отдавать vk=67 и char=None.
        vk = getattr(key, "vk", None)
        if vk == 67:
            return True
        if isinstance(key, keyboard.KeyCode):
            ch = getattr(key, "char", None)
            if ch and ch.lower() == "c":
                return True
        return False

    def _on_press(self, key) -> None:
        with self._lock:
            if self._is_ctrl(key):
                self._ctrl_down = True
                return

            if self._is_c(key):
                # Автоповтор: C↓ без промежуточного C↑ — игнор.
                if self._c_is_down:
                    return
                self._c_is_down = True

                if not self._ctrl_down:
                    # C без Ctrl — состояние двойного клика сбрасываем.
                    self._c_pressed_once = False
                    return

                now = time.monotonic()
                if self._c_pressed_once and (now - self._last_c_press_ts) <= self._window:
                    # Двойное C при зажатом Ctrl → триггер.
                    self._c_pressed_once = False
                    self._last_c_press_ts = 0.0
                    fire = True
                else:
                    self._c_pressed_once = True
                    self._last_c_press_ts = now
                    fire = False

            else:
                return

        if fire:
            try:
                self._on_trigger()
            except Exception:
                pass

    def _on_release(self, key) -> None:
        with self._lock:
            if self._is_ctrl(key):
                self._ctrl_down = False
                self._c_pressed_once = False
                self._last_c_press_ts = 0.0
                return
            if self._is_c(key):
                self._c_is_down = False
