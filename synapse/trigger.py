from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock

from pynput import keyboard

Callback = Callable[[], None]


class DoubleCtrlCTrigger:
    """Listener for Ctrl+C+C.

    Fires when, with Ctrl held down continuously, two C key presses occur
    (C-down, C-up, C-down) and the second C-down falls within
    double_c_window_ms of the first. OS autorepeat events (C-down with no
    intervening C-up) are ignored. Releasing Ctrl resets the state.

    The listener does not block keys — the first Ctrl+C works as usual.
    """

    def __init__(self, on_trigger: Callback, window_ms: int = 400) -> None:
        self._on_trigger = on_trigger
        self._window = window_ms / 1000.0
        self._ctrl_down = False
        self._c_pressed_once = False  # at least one completed C press while Ctrl was held
        self._last_c_press_ts = 0.0
        self._c_is_down = False  # current physical state of the C key (for autorepeat filtering)
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
        # With Ctrl held, pynput on Windows may report vk=67 and char=None.
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
                # Autorepeat: C-down without intervening C-up — ignore.
                if self._c_is_down:
                    return
                self._c_is_down = True

                if not self._ctrl_down:
                    # C without Ctrl — reset the double-press state.
                    self._c_pressed_once = False
                    return

                now = time.monotonic()
                if self._c_pressed_once and (now - self._last_c_press_ts) <= self._window:
                    # Double C while Ctrl is held → trigger.
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
