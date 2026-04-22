from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QPoint, QSize, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication, QKeyEvent, QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from pynput import mouse as pynput_mouse

RESIZE_MARGIN = 6  # толщина невидимой рамки для хвата курсором
TITLEBAR_H = 28    # высота зоны, за которую можно таскать окно


class PopupWindow(QWidget):
    _outside_click = Signal()

    def __init__(self, default_width: int = 320,
                 cursor_offset_x: int = 16, cursor_offset_y: int = 16) -> None:
        super().__init__(None)
        self._default_width = default_width
        self._cursor_off = (cursor_offset_x, cursor_offset_y)
        self._current_translation = ""
        self._user_size: QSize | None = None  # None пока пользователь сам не ресайзил

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
        self.setMinimumSize(220, 120)

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
            QLabel#header { color: #9aa0a6; font-size: 11px; letter-spacing: 1px; }
            QLabel#original { color: #8c9196; font-size: 12px; }
            QLabel#translation { color: #ffffff; font-size: 15px; }
            QPushButton {
                background: #2c2e33; color: #e8e8e8;
                border: 1px solid #45474d; border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #3a3c42; }
            QPushButton:pressed { background: #24262a; }
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN, RESIZE_MARGIN)
        outer.addWidget(self._frame)

        root = QVBoxLayout(self._frame)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        header_row = QHBoxLayout()
        self._header = QLabel("…")
        self._header.setObjectName("header")
        self._header.setCursor(Qt.CursorShape.IBeamCursor)
        header_row.addWidget(self._header)
        header_row.addStretch(1)
        self._copy_btn = QPushButton("Скопировать")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._copy_btn.clicked.connect(self._copy_translation)
        header_row.addWidget(self._copy_btn)
        root.addLayout(header_row)

        self._scroll = QScrollArea(self._frame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        self._translation_label = QLabel("Переводится…")
        self._translation_label.setObjectName("translation")
        self._translation_label.setWordWrap(True)
        self._translation_label.setTextFormat(Qt.TextFormat.PlainText)
        self._translation_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._translation_label.setCursor(Qt.CursorShape.IBeamCursor)
        inner_layout.addWidget(self._translation_label)
        inner_layout.addStretch(1)
        self._scroll.setWidget(inner)
        root.addWidget(self._scroll, 1)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.addStretch(1)
        self._grip = QSizeGrip(self)
        self._grip.setFixedSize(16, 16)
        self._grip.setToolTip("Потяни, чтобы изменить размер")
        bottom_row.addWidget(self._grip, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        root.addLayout(bottom_row)

        self._mouse_listener: pynput_mouse.Listener | None = None
        self._outside_click.connect(self._on_outside_click)

        # Ручной resize по краям
        self._resize_edge: str | None = None
        self._resize_start_geom = None
        self._resize_start_pos = None

        # Перетаскивание окна
        self._drag_offset: QPoint | None = None
        self._current_cursor_shape: Qt.CursorShape | None = None

        # Включаем mouse tracking на всех дочерних виджетах и ставим event filter,
        # чтобы получать MouseMove/MouseButtonPress даже над детьми.
        self._install_mouse_hooks(self)

    def _install_mouse_hooks(self, widget: QWidget) -> None:
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.setMouseTracking(True)
            child.installEventFilter(self)

    # --- public API ---------------------------------------------------------

    def show_loading(self, header: str) -> None:
        self._header.setText(header)
        self._current_translation = ""
        self._copy_btn.setEnabled(False)
        self._translation_label.setText("Переводится…")
        self._reposition_and_show()

    def show_translation(self, translation: str) -> None:
        self._current_translation = translation
        self._translation_label.setText(translation)
        self._copy_btn.setEnabled(bool(translation))
        self._fit_height_to_content()

    def show_error(self, message: str) -> None:
        self._current_translation = ""
        self._copy_btn.setEnabled(False)
        self._translation_label.setText(message)
        self._fit_height_to_content()

    # --- internals ----------------------------------------------------------

    def _reposition_and_show(self) -> None:
        if self._user_size is not None:
            self.resize(self._user_size)
        else:
            self.resize(self._default_width, max(140, self.minimumSizeHint().height()))

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

    def _fit_height_to_content(self) -> None:
        # Ширину не трогаем — её выбрал пользователь или дефолт.
        width = self.width()

        # Ширина, достающаяся тексту внутри scroll area.
        # outer layout: по RESIZE_MARGIN слева/справа; root_layout: 12 + 12.
        text_w = max(50, width - 2 * RESIZE_MARGIN - 24)

        # Высота, нужная самому тексту при этой ширине (с учётом wordWrap).
        self._translation_label.adjustSize()
        text_h = self._translation_label.heightForWidth(text_w)
        if text_h < 0:
            text_h = self._translation_label.sizeHint().height()

        # Высота остального «хрома» (заголовок-строка, кнопка, grip, отступы).
        header_row_h = max(self._header.sizeHint().height(), self._copy_btn.sizeHint().height())
        grip_row_h = self._grip.height() if hasattr(self, "_grip") else 16
        root_margins = self._frame.layout().contentsMargins()
        root_spacing = self._frame.layout().spacing()
        chrome_h = (
            2 * RESIZE_MARGIN                     # outer layout
            + root_margins.top() + root_margins.bottom()
            + header_row_h
            + grip_row_h
            + 2 * max(root_spacing, 0)            # 2 промежутка: header↔scroll, scroll↔grip
            + 4                                   # небольшой запас на рамки/округления
        )

        content_h = text_h + chrome_h
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        max_h = int(screen.availableGeometry().height() * 0.7)
        new_h = max(self.minimumHeight(), min(content_h, max_h))
        if new_h != self.height():
            self.resize(width, new_h)

    def _copy_translation(self) -> None:
        if not self._current_translation:
            return
        cb = QApplication.clipboard()
        cb.setText(self._current_translation, QClipboard.Mode.Clipboard)
        self._copy_btn.setText("Скопировано")
        QTimer.singleShot(1200, lambda: self._copy_btn.setText("Скопировать"))

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)

    # --- resize через края окна --------------------------------------------

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
        """Держит ровно один активный override-курсор.
        Передай shape, чтобы поставить/заменить, и None чтобы снять."""
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
        # Не на краю. Находим дочерний виджет под курсором и берём его shape.
        local = self.mapFromGlobal(gp)
        child = self.childAt(local)
        shape: Qt.CursorShape | None = None
        w = child
        while w is not None and w is not self:
            if w is self._translation_label or w is self._header:
                shape = Qt.CursorShape.IBeamCursor
                break
            if w is self._copy_btn:
                shape = Qt.CursorShape.PointingHandCursor
                break
            w = w.parentWidget()
        self._set_override_cursor(shape)

    def eventFilter(self, obj, event):  # noqa: N802
        et = event.type()
        if et == QEvent.Type.MouseMove:
            # глобальная позиция мыши
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
                    return True  # глотаем — ресайз важнее любых кликов под курсором
                if self._in_titlebar_global(gp) and obj is self._frame:
                    # Только клик по самому frame (а не по кнопке/метке) инициирует drag.
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
        if not self.isVisible():
            return
        if not self.frameGeometry().contains(QPoint(int(x), int(y))):
            self._outside_click.emit()

    def _on_outside_click(self) -> None:
        self.hide()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._stop_outside_listener()
        self._set_override_cursor(None)
        super().hideEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_outside_listener()
        self._set_override_cursor(None)
        super().closeEvent(event)
