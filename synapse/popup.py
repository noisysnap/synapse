from __future__ import annotations

import sys
from time import monotonic as _monotonic

from PySide6.QtCore import Qt, QEvent, QPoint, QSize, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QKeyEvent, QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard

from .config import debug_enabled
from .i18n import t
from .lang import POPULAR_LANGUAGES, language_display
from .lang_picker import LangPicker
from .tray import app_icon


def _dbg(*a) -> None:
    if debug_enabled():
        print("[synapse/popup]", *a, file=sys.stderr, flush=True)


RESIZE_MARGIN = 6  # invisible edge thickness reserved for resize-grab
TITLEBAR_H = 28    # height of the drag-handle strip at the top


class PopupWindow(QWidget):
    _outside_click = Signal(int, int)
    dst_language_changed = Signal(str)
    src_language_changed = Signal(str)
    edit_requested = Signal()

    def __init__(self, default_width: int = 480, default_height: int = 320,
                 cursor_offset_x: int = 16, cursor_offset_y: int = 16,
                 preferred_dst: str = "en",
                 close_on_copy: bool = False) -> None:
        super().__init__(None)
        self.setWindowIcon(app_icon())
        self._default_width = default_width
        self._default_height = default_height
        self._cursor_off = (cursor_offset_x, cursor_offset_y)
        self._current_translation = ""
        self._source_hwnd: int | None = None  # HWND of the window that was active before the popup
        self._user_size: QSize | None = None  # None until the user resizes manually
        self._preferred_dst = preferred_dst
        self._preferred_src = "en"
        self._close_on_copy = close_on_copy

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        self.setMinimumSize(280, 220)

        self._frame = QFrame(self)
        self._frame.setObjectName("popupFrame")
        self._frame.setStyleSheet("""
            #popupFrame {
                background: #1f2024;
                color: #f0f0f0;
                border: 1px solid #3a3b40;
                border-radius: 8px;
            }
            QLabel { color: #f0f0f0; }
            QLabel#arrow { color: #9aa0a6; font-size: 11px; }
            QLabel#updating {
                color: #9aa0a6;
                font-size: 11px;
                font-style: italic;
                padding-left: 6px;
            }
            QPlainTextEdit#translation {
                background: transparent;
                color: #ffffff;
                font-size: 15px;
                border: none;
                selection-background-color: #3a7afe;
                selection-color: #ffffff;
            }
            QPushButton {
                background: #2c2e33; color: #e8e8e8;
                border: 1px solid #45474d; border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #3a3c42; }
            QPushButton:pressed { background: #24262a; }
            QToolButton#langCombo {
                background: transparent;
                color: #c5c9cf;
                border: none;
                padding: 2px 6px;
                font-size: 11px;
                letter-spacing: 1px;
            }
            QToolButton#langCombo:hover { color: #ffffff; }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN)
        outer.addWidget(self._frame)

        root = QVBoxLayout(self._frame)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        lang_items = [(code, language_display(code, name)) for code, name in POPULAR_LANGUAGES]

        header_row.addStretch(1)

        self._src_combo = LangPicker(lang_items)
        self._src_combo.setObjectName("langCombo")
        self._src_combo.setToolTip(t("popup.src_tooltip"))
        self._src_combo.set_value(self._preferred_src)
        self._src_combo.value_changed.connect(self._on_src_lang_changed)
        self._src_combo.dropdown_opened.connect(self._on_dropdown_open)
        self._src_combo.dropdown_closed.connect(self._on_dropdown_close)
        header_row.addWidget(self._src_combo)

        self._arrow_label = QLabel("→")
        self._arrow_label.setObjectName("arrow")
        header_row.addWidget(self._arrow_label)

        self._lang_combo = LangPicker(lang_items)
        self._lang_combo.setObjectName("langCombo")
        self._lang_combo.setToolTip(t("popup.dst_tooltip"))
        self._lang_combo.set_value(self._preferred_dst)
        self._lang_combo.value_changed.connect(self._on_lang_changed)
        self._lang_combo.dropdown_opened.connect(self._on_dropdown_open)
        self._lang_combo.dropdown_closed.connect(self._on_dropdown_close)
        header_row.addWidget(self._lang_combo)

        self._updating_label = QLabel("")
        self._updating_label.setObjectName("updating")
        self._updating_label.hide()
        header_row.addWidget(self._updating_label)

        header_row.addStretch(1)

        root.addLayout(header_row)

        self._translation_view = QPlainTextEdit(self._frame)
        self._translation_view.setObjectName("translation")
        self._translation_view.setReadOnly(True)
        self._translation_view.setFrameShape(QFrame.Shape.NoFrame)
        self._translation_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._translation_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._translation_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._translation_view.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._translation_view.setCursor(Qt.CursorShape.IBeamCursor)
        self._translation_view.setPlainText(t("popup.translating"))
        # Inner text padding — set a small amount so text does not stick
        # to the scrollbar edge or the frame border.
        self._translation_view.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._translation_view, 1)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(6)

        self._edit_btn = QPushButton(t("popup.edit"))
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        bottom_row.addWidget(self._edit_btn, 0, Qt.AlignmentFlag.AlignBottom)

        bottom_row.addStretch(1)

        self._copy_btn = QPushButton(t("popup.copy"))
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._copy_btn.clicked.connect(self._copy_translation)
        bottom_row.addWidget(self._copy_btn, 0, Qt.AlignmentFlag.AlignBottom)

        self._paste_btn = QPushButton(t("popup.paste"))
        self._paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._paste_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._paste_btn.clicked.connect(self._paste_translation)
        self._paste_btn.setEnabled(False)
        bottom_row.addWidget(self._paste_btn, 0, Qt.AlignmentFlag.AlignBottom)

        self._grip = QSizeGrip(self)
        self._grip.setFixedSize(16, 16)
        self._grip.setToolTip(t("popup.resize_tooltip"))
        bottom_row.addWidget(self._grip, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        root.addLayout(bottom_row)

        self._mouse_listener: pynput_mouse.Listener | None = None
        self._dropdown_suppress_until: float = 0.0
        self._outside_click.connect(self._on_outside_click)

        self._streaming: bool = False

        # Manual edge-based resize
        self._resize_edge: str | None = None
        self._resize_start_geom = None
        self._resize_start_pos = None

        # Window drag
        self._drag_offset: QPoint | None = None
        self._current_cursor_shape: Qt.CursorShape | None = None

        # Enable mouse tracking on all child widgets and install an event
        # filter so we receive MouseMove/MouseButtonPress over children too.
        self._install_mouse_hooks(self)

    def _install_mouse_hooks(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.setMouseTracking(True)
            child.installEventFilter(self)

    # --- public API ---------------------------------------------------------

    def set_preferred_dst(self, code: str) -> None:
        """Set the selected language from outside without emitting a signal."""
        self._preferred_dst = code
        self._lang_combo.set_value(code)

    def set_close_on_copy(self, enabled: bool) -> None:
        self._close_on_copy = bool(enabled)

    def apply_ui_language(self) -> None:
        """Refresh static strings after a UI language change."""
        self._src_combo.setToolTip(t("popup.src_tooltip"))
        self._lang_combo.setToolTip(t("popup.dst_tooltip"))
        self._copy_btn.setText(t("popup.copy"))
        self._paste_btn.setText(t("popup.paste"))
        self._edit_btn.setText(t("popup.edit"))
        self._grip.setToolTip(t("popup.resize_tooltip"))
        if not self._streaming and not self._current_translation:
            text = self._translation_view.toPlainText()
            if text in ("Переводится…", "Translating…", ""):
                self._translation_view.setPlainText(t("popup.translating"))

    def _on_lang_changed(self, code: str) -> None:
        _dbg(f"_on_lang_changed code={code}")
        if code == self._preferred_dst:
            return
        self._preferred_dst = code
        self.dst_language_changed.emit(code)

    def _on_src_lang_changed(self, code: str) -> None:
        _dbg(f"_on_src_lang_changed code={code}")
        if code == self._preferred_src:
            return
        self._preferred_src = code
        self.src_language_changed.emit(code)

    def set_direction(self, src: str, dst: str) -> None:
        """Update the displayed direction without restarting the animation.

        Syncs both combos (without emitting signals). Does not touch the
        translation text — it will be overwritten by
        begin_translation / append_translation."""
        self._src_combo.set_value(src)
        self._lang_combo.set_value(dst)
        self._preferred_src = src
        self._preferred_dst = dst

    def _set_actions_enabled(self, enabled: bool) -> None:
        self._copy_btn.setEnabled(enabled)
        self._paste_btn.setEnabled(enabled)

    def show_loading(self, src: str, dst: str) -> None:
        self.set_direction(src, dst)
        self._current_translation = ""
        self._set_actions_enabled(False)
        self._translation_view.setPlainText(t("popup.translating"))
        self._reposition_and_show()

    def show_translation(self, translation: str) -> None:
        self._streaming = False
        self._current_translation = translation
        self._translation_view.setPlainText(translation)
        self._scroll_to_top()
        self._set_actions_enabled(bool(translation))

    def begin_translation(self) -> None:
        """Start accumulating a streaming translation. Clears the field,
        then waits for the first delta."""
        self._streaming = True
        self._current_translation = ""
        self._translation_view.setPlainText("")
        self._set_actions_enabled(False)

    def begin_soft_replace(self) -> None:
        """Soft start: keep the old text visible to avoid flashing. The
        first append_translation call overwrites it."""
        self._streaming = True
        self._current_translation = ""
        self._set_actions_enabled(False)
        self._show_updating(t("popup.updating"))

    def append_translation(self, delta: str) -> None:
        """Append the next translation chunk."""
        if not delta:
            return
        first_chunk = self._current_translation == ""
        self._streaming = True
        self._current_translation += delta
        # On a soft-replace the first chunk overwrites the old text.
        self._translation_view.setPlainText(self._current_translation)
        if first_chunk:
            self._hide_updating()
            self._scroll_to_top()
        self._set_actions_enabled(True)

    def _show_updating(self, text: str) -> None:
        self._updating_label.setText(text)
        self._updating_label.show()

    def _hide_updating(self) -> None:
        self._updating_label.hide()

    def _scroll_to_top(self) -> None:
        bar = self._translation_view.verticalScrollBar()
        if bar is not None:
            bar.setValue(0)

    def finish_translation(self) -> None:
        """Mark the stream as finished."""
        self._streaming = False
        self._hide_updating()

    def show_error(self, message: str) -> None:
        self._streaming = False
        self._hide_updating()
        self._current_translation = ""
        self._set_actions_enabled(False)
        self._translation_view.setPlainText(message)
        self._scroll_to_top()

    # --- internals ----------------------------------------------------------

    def remember_source_window(self) -> None:
        """Remember which window was in the foreground before the popup
        appeared — so that focus can later be returned to it and Ctrl+V
        sent there."""
        hwnd = self._capture_foreground_hwnd()
        # Ignore if the foreground is the popup itself (a repeat trigger
        # on top of an already-open window). The previous _source_hwnd
        # is still valid in that case.
        own = int(self.winId()) if self.isVisible() else 0
        if hwnd and hwnd != own:
            self._source_hwnd = hwnd
        _dbg(f"remember_source_window captured={hwnd} own={own} stored={self._source_hwnd}")

    def _reposition_and_show(self) -> None:
        if self._user_size is not None:
            self.resize(self._user_size)
        else:
            default_h = max(self._default_height, self.minimumSizeHint().height())
            self.resize(self._default_width, default_h)

        cursor_pos = QCursor.pos()
        ox, oy = self._cursor_off
        target = QPoint(cursor_pos.x() + ox, cursor_pos.y() + oy)

        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        w = self.width()
        h = self.height()

        x = max(geo.left(), min(target.x(), geo.right() - w))
        y = max(geo.top(), min(target.y(), geo.bottom() - h))
        self.move(x, y)

        if not self.isVisible():
            self.show()
        else:
            self.raise_()

        self._start_outside_listener()

    def _copy_translation(self) -> None:
        if not self._current_translation:
            return
        cb = QApplication.clipboard()
        cb.setText(self._current_translation, QClipboard.Mode.Clipboard)
        if self._close_on_copy:
            self.hide()
            QTimer.singleShot(120, self._restore_source_foreground)
            return
        self._copy_btn.setText(t("popup.copied"))
        QTimer.singleShot(1200, lambda: self._copy_btn.setText(t("popup.copy")))

    def _restore_source_foreground(self) -> None:
        """Return focus to the window the source was copied from (no key send)."""
        target = self._source_hwnd
        if sys.platform == "win32" and target:
            restored = self._restore_foreground(target)
            _dbg(f"close_on_copy restore_foreground hwnd={target} restored={restored}")

    def _paste_translation(self) -> None:
        """Put the translation on the clipboard and send Ctrl+V to the
        active window, replacing the selected original with the translation."""
        if not self._current_translation:
            return
        cb = QApplication.clipboard()
        cb.setText(self._current_translation, QClipboard.Mode.Clipboard)
        # Hide the popup so focus reliably returns to the target window.
        self.hide()
        # The delay gives the OS time to move the popup off the foreground
        # and drain Qt's queue. Then we force focus back to the source
        # window and dispatch Ctrl+V.
        QTimer.singleShot(120, self._do_paste_into_source)

    def _capture_foreground_hwnd(self) -> int | None:
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            hwnd = int(ctypes.windll.user32.GetForegroundWindow())
            return hwnd or None
        except Exception as e:
            _dbg(f"GetForegroundWindow failed: {e}")
            return None

    def _restore_foreground(self, hwnd: int) -> bool:
        """Bring focus to hwnd via the AttachThreadInput trick.
        Windows forbids SetForegroundWindow without explicit user input,
        but attaching to the thread that owns the current foreground
        lifts the restriction."""
        if sys.platform != "win32" or not hwnd:
            return False
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            if not user32.IsWindow(hwnd):
                _dbg(f"restore_foreground: hwnd={hwnd} is no longer valid")
                return False

            # If the window is minimised, restore it.
            SW_RESTORE = 9
            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, SW_RESTORE)

            fg = user32.GetForegroundWindow()
            if fg == hwnd:
                return True

            fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
            target_thread = user32.GetWindowThreadProcessId(hwnd, None)
            cur_thread = kernel32.GetCurrentThreadId()

            attached_fg = False
            attached_target = False
            try:
                if fg_thread and fg_thread != cur_thread:
                    attached_fg = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
                if target_thread and target_thread != cur_thread and target_thread != fg_thread:
                    attached_target = bool(user32.AttachThreadInput(cur_thread, target_thread, True))
                user32.BringWindowToTop(hwnd)
                ok = bool(user32.SetForegroundWindow(hwnd))
                return ok
            finally:
                if attached_fg:
                    user32.AttachThreadInput(cur_thread, fg_thread, False)
                if attached_target:
                    user32.AttachThreadInput(cur_thread, target_thread, False)
        except Exception as e:
            _dbg(f"restore_foreground failed: {e}")
            return False

    def _do_paste_into_source(self) -> None:
        target = self._source_hwnd
        if sys.platform == "win32" and target:
            restored = self._restore_foreground(target)
            _dbg(f"restore_foreground hwnd={target} restored={restored}")
            # Another short delay — Windows needs time to switch focus
            # after AttachThreadInput/SetForegroundWindow.
            QTimer.singleShot(40, self._send_paste_keystroke)
            return
        self._send_paste_keystroke()

    def _send_paste_keystroke(self) -> None:
        """Send Ctrl+V via Windows SendInput using virtual key codes.
        Layout-independent (unlike sending the 'v' character, which on a
        Russian layout becomes 'м')."""
        if sys.platform != "win32":
            # Fallback for non-Windows — pynput with the character.
            try:
                kb = pynput_keyboard.Controller()
                with kb.pressed(pynput_keyboard.Key.ctrl):
                    kb.press('v')
                    kb.release('v')
            except Exception as e:
                _dbg(f"paste keystroke failed: {e}")
            return

        try:
            import ctypes
            from ctypes import wintypes

            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002
            INPUT_KEYBOARD = 1

            ULONG_PTR = ctypes.c_size_t

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = (
                    ("dx", wintypes.LONG),
                    ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR),
                )

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = (
                    ("wVk", wintypes.WORD),
                    ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR),
                )

            class HARDWAREINPUT(ctypes.Structure):
                _fields_ = (
                    ("uMsg", wintypes.DWORD),
                    ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD),
                )

            # The union must include MOUSEINPUT so its size matches the
            # real WinAPI INPUT (40 bytes on x64). Without MOUSEINPUT the
            # struct is 32 bytes and SendInput returns
            # ERROR_INVALID_PARAMETER (87).
            class _INPUTunion(ctypes.Union):
                _fields_ = (
                    ("mi", MOUSEINPUT),
                    ("ki", KEYBDINPUT),
                    ("hi", HARDWAREINPUT),
                )

            class INPUT(ctypes.Structure):
                _anonymous_ = ("u",)
                _fields_ = (
                    ("type", wintypes.DWORD),
                    ("u", _INPUTunion),
                )

            def make(vk: int, up: bool) -> INPUT:
                flags = KEYEVENTF_KEYUP if up else 0
                return INPUT(
                    type=INPUT_KEYBOARD,
                    u=_INPUTunion(ki=KEYBDINPUT(vk, 0, flags, 0, 0)),
                )

            seq = (INPUT * 4)(
                make(VK_CONTROL, False),
                make(VK_V, False),
                make(VK_V, True),
                make(VK_CONTROL, True),
            )
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            user32.SendInput.argtypes = (wintypes.UINT, ctypes.c_void_p, ctypes.c_int)
            user32.SendInput.restype = wintypes.UINT
            kernel32.SetLastError(0)
            sent = user32.SendInput(4, ctypes.byref(seq), ctypes.sizeof(INPUT))
            err = kernel32.GetLastError()
            fg_after = user32.GetForegroundWindow()
            _dbg(
                f"SendInput Ctrl+V sent={sent}/4 last_error={err} "
                f"input_size={ctypes.sizeof(INPUT)} foreground_after={fg_after}"
            )
        except Exception as e:
            _dbg(f"paste SendInput failed: {e}")

    def current_translation(self) -> str:
        return self._current_translation

    def _on_edit_clicked(self) -> None:
        self.edit_requested.emit()
        self.hide()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    # --- edge-based resize -------------------------------------------------

    def _edge_at(self, pos: QPoint) -> str | None:
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = RESIZE_MARGIN
        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m
        if right and bottom:
            return "br"
        if left and bottom:
            return "bl"
        if right and top:
            return "tr"
        if left and top:
            return "tl"
        if right:
            return "r"
        if left:
            return "l"
        if bottom:
            return "b"
        if top:
            return "t"
        return None

    _EDGE_CURSORS = {
        "l": Qt.CursorShape.SizeHorCursor,
        "r": Qt.CursorShape.SizeHorCursor,
        "t": Qt.CursorShape.SizeVerCursor,
        "b": Qt.CursorShape.SizeVerCursor,
        "tl": Qt.CursorShape.SizeFDiagCursor,
        "br": Qt.CursorShape.SizeFDiagCursor,
        "tr": Qt.CursorShape.SizeBDiagCursor,
        "bl": Qt.CursorShape.SizeBDiagCursor,
    }

    def _edge_at_global(self, gp: QPoint) -> str | None:
        return self._edge_at(self.mapFromGlobal(gp))

    def _in_titlebar_global(self, gp: QPoint) -> bool:
        pos = self.mapFromGlobal(gp)
        if not self.rect().contains(pos):
            return False
        w = self.width()
        x, y = pos.x(), pos.y()
        return (
            RESIZE_MARGIN < y < RESIZE_MARGIN + TITLEBAR_H
            and RESIZE_MARGIN < x < w - RESIZE_MARGIN
        )

    def _set_override_cursor(self, shape: Qt.CursorShape | None) -> None:
        """Keep exactly one active override cursor.
        Pass a shape to set/replace, or None to clear."""
        current = self._current_cursor_shape
        if shape is None:
            if current is not None:
                QGuiApplication.restoreOverrideCursor()
                self._current_cursor_shape = None
            return
        if current is None:
            QGuiApplication.setOverrideCursor(QCursor(shape))
        elif current != shape:
            QGuiApplication.changeOverrideCursor(QCursor(shape))
        self._current_cursor_shape = shape

    def _update_cursor_for_global(self, gp: QPoint) -> None:
        if self._resize_edge is not None or self._drag_offset is not None:
            return
        if not self.isVisible() or not self.frameGeometry().contains(gp):
            self._set_override_cursor(None)
            return
        edge = self._edge_at_global(gp)
        if edge is not None:
            self._set_override_cursor(self._EDGE_CURSORS[edge])
            return
        # Not on an edge. Locate the child under the cursor and use its shape.
        local = self.mapFromGlobal(gp)
        child = self.childAt(local)
        shape: Qt.CursorShape | None = None
        w = child
        while w is not None and w is not self:
            if w is self._translation_view or w is self._translation_view.viewport():
                shape = Qt.CursorShape.IBeamCursor
                break
            if (w is self._copy_btn or w is self._edit_btn
                    or w is self._lang_combo or w is self._src_combo):
                shape = Qt.CursorShape.PointingHandCursor
                break
            w = w.parentWidget()
        self._set_override_cursor(shape)

    def eventFilter(self, obj, event):  # noqa: N802
        et = event.type()
        if et == QEvent.Type.MouseMove:
            # global mouse position
            try:
                gp = event.globalPosition().toPoint()
            except AttributeError:
                gp = event.globalPos()
            if self._resize_edge is not None:
                self._apply_resize(gp)
            elif self._drag_offset is not None:
                self.move(gp - self._drag_offset)
            else:
                self._update_cursor_for_global(gp)
        elif et == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                try:
                    gp = event.globalPosition().toPoint()
                except AttributeError:
                    gp = event.globalPos()
                edge = self._edge_at_global(gp)
                if edge is not None:
                    self._resize_edge = edge
                    self._resize_start_geom = self.geometry()
                    self._resize_start_pos = gp
                    return True  # swallow — resize takes priority over any clicks underneath
                if self._in_titlebar_global(gp) and obj is self._frame:
                    # Only a click on the frame itself (not on a button or
                    # label) starts the drag.
                    self._drag_offset = gp - self.frameGeometry().topLeft()
                    return True
        elif et == QEvent.Type.MouseButtonRelease:
            if self._resize_edge is not None:
                self._resize_edge = None
                self._user_size = self.size()
            if self._drag_offset is not None:
                self._drag_offset = None
        return super().eventFilter(obj, event)

    def enterEvent(self, event):  # noqa: N802
        try:
            gp = event.globalPosition().toPoint()
        except AttributeError:
            gp = QCursor.pos()
        self._update_cursor_for_global(gp)
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        if self._resize_edge is None and self._drag_offset is None:
            self._set_override_cursor(None)
        super().leaveEvent(event)

    def _apply_resize(self, global_pos: QPoint) -> None:
        if self._resize_start_geom is None or self._resize_start_pos is None:
            return
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        g = self._resize_start_geom
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        x, y, w, h = g.x(), g.y(), g.width(), g.height()
        edge = self._resize_edge or ""
        if "r" in edge:
            w = max(min_w, g.width() + dx)
        if "l" in edge:
            new_w = max(min_w, g.width() - dx)
            x = g.x() + (g.width() - new_w)
            w = new_w
        if "b" in edge:
            h = max(min_h, g.height() + dy)
        if "t" in edge:
            new_h = max(min_h, g.height() - dy)
            y = g.y() + (g.height() - new_h)
            h = new_h
        self.setGeometry(x, y, w, h)

    # --- outside click via pynput ------------------------------------------

    def _start_outside_listener(self) -> None:
        if self._mouse_listener is not None:
            return
        self._mouse_listener = pynput_mouse.Listener(on_click=self._on_global_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

    def _stop_outside_listener(self) -> None:
        if self._mouse_listener is None:
            return
        try:
            self._mouse_listener.stop()
        except Exception:
            pass
        self._mouse_listener = None

    def _on_global_click(self, x, y, button, pressed) -> None:
        if not pressed:
            return
        now = _monotonic()
        remaining = self._dropdown_suppress_until - now
        popup_geo = self.frameGeometry()
        _dbg(
            f"pynput pressed at ({x},{y}) | suppress_remaining={remaining:.3f}s "
            f"popup=[{popup_geo.x()},{popup_geo.y()} {popup_geo.width()}x{popup_geo.height()}]"
        )
        # While a combobox dropdown is open — and for a short window after
        # it closes — leave the popup alone. Otherwise a click on an item
        # extending past the popup's bounds is treated as an outside-click
        # and the popup hides before Qt applies the selection.
        if remaining > 0:
            _dbg("  → suppressed (dropdown cooldown)")
            return
        # pynput callback runs on its own thread — defer Qt checks to the slot.
        self._outside_click.emit(int(x), int(y))

    def _on_dropdown_open(self) -> None:
        self._dropdown_suppress_until = _monotonic() + 30.0
        _dbg(f"dropdown OPEN (suppress_until=+30s), stopping pynput listener")
        # Stop pynput entirely while a dropdown is open. The WH_MOUSE_LL
        # hook can distort or delay Windows click messages enough that
        # the dropdown container never receives them.
        self._stop_outside_listener()

    def _on_dropdown_close(self) -> None:
        # The suppress window matches the listener-restart delay, so there
        # is no gap between restart and suppress release.
        self._dropdown_suppress_until = _monotonic() + 0.30
        _dbg(f"dropdown CLOSE (suppress_until=+0.30s), restarting pynput")
        # Bring pynput back. The short delay lets Qt process the
        # click-inside-dropdown without the hook getting in the way.
        QTimer.singleShot(300, self._restart_outside_listener_if_visible)

    def _restart_outside_listener_if_visible(self) -> None:
        # The popup could have hidden during the 300ms between dropdown
        # CLOSE and the restart. Starting the listener then is pointless —
        # it would survive until the next hide/close. Restart only if the
        # window is still visible.
        if not self.isVisible():
            _dbg("restart listener skipped — popup hidden")
            return
        self._start_outside_listener()

    def _on_outside_click(self, x: int, y: int) -> None:
        _dbg(f"_on_outside_click slot fired at ({x},{y}) visible={self.isVisible()}")
        if not self.isVisible():
            return
        pt = QPoint(x, y)
        if self.frameGeometry().contains(pt):
            _dbg("  inside frameGeometry → ignore")
            return
        active_popup = QApplication.activePopupWidget()
        _dbg(f"  activePopupWidget={active_popup}")
        if active_popup is not None and active_popup is not self:
            try:
                if active_popup.geometry().contains(pt):
                    _dbg("  click inside active popup → ignore")
                    return
            except Exception:
                pass
        w_at = QApplication.widgetAt(pt)
        _dbg(f"  widgetAt={w_at}")
        if w_at is not None:
            top = w_at.window()
            if top is not None and top is not self:
                flags = top.windowFlags()
                if flags & Qt.WindowType.Popup:
                    _dbg("  widgetAt top is Popup → ignore")
                    return
        _dbg("  → HIDING popup")
        self.hide()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._stop_outside_listener()
        self._set_override_cursor(None)
        super().hideEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_outside_listener()
        self._set_override_cursor(None)
        super().closeEvent(event)
