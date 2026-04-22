from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class _LangPickerPopup(QWidget):
    """Собственный dropdown-список языков как отдельное top-level окно.

    Стандартный QComboBox dropdown на Windows страдает от проблем со z-order
    при родителе с WindowStaysOnTopHint: визуально виден, но клики по пунктам,
    выходящим за пределы родительского окна, физически не доходят до Qt.
    Собственное top-level Qt.Popup-окно с явно выставленными флагами
    стабильно получает клики и корректно закрывается по outside-click."""

    selected = Signal(str)  # emit(code)
    closed = Signal()

    def __init__(self, items: list[tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent,
                         Qt.WindowType.Popup
                         | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self._pending_code: str | None = None
        self._list = QListWidget(self)
        self._list.setObjectName("langList")
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setUniformItemSizes(True)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        for code, label in items:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, code)
            self._list.addItem(item)
        self._list.itemClicked.connect(self._on_item_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._list)

        self.setStyleSheet("""
            QWidget {
                background: #2c2e33;
                border: 1px solid #45474d;
            }
            QListWidget#langList {
                background: #2c2e33;
                color: #e8e8e8;
                outline: none;
                padding: 2px 0;
            }
            QListWidget#langList::item {
                padding: 4px 12px;
            }
            QListWidget#langList::item:selected,
            QListWidget#langList::item:hover {
                background: #3a7afe;
                color: #ffffff;
            }
        """)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        code = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(code, str):
            self._pending_code = code
        self.hide()

    def show_at(self, global_pos: QPoint, min_width: int) -> None:
        self._list.setMinimumWidth(min_width)
        fm_h = self._list.sizeHintForRow(0) if self._list.count() > 0 else 20
        count_to_show = min(self._list.count(), 10)
        content_h = fm_h * count_to_show + 6
        self.resize(max(min_width, self._list.sizeHint().width()), content_h)
        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = max(geo.left(), min(global_pos.x(), geo.right() - self.width()))
        y = global_pos.y()
        if y + self.height() > geo.bottom():
            y = max(geo.top(), global_pos.y() - self.height())
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event) -> None:  # noqa: N802
        super().hideEvent(event)
        code = self._pending_code
        self._pending_code = None
        if code is not None:
            self.selected.emit(code)
        self.closed.emit()


class LangPicker(QToolButton):
    """Кнопка-«комбобокс», открывающая собственный top-level popup-список.

    Сигнализирует через dropdown_opened / dropdown_closed / value_changed."""

    dropdown_opened = Signal()
    dropdown_closed = Signal()
    value_changed = Signal(str)

    def __init__(self, items: list[tuple[str, str]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items = list(items)  # [(code, label)]
        self._code_to_label = {code: label for code, label in items}
        self._current: str = items[0][0] if items else ""
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.DelayedPopup)
        self.clicked.connect(self._show_picker)
        self._picker: _LangPickerPopup | None = None
        self._refresh_text()

    def _refresh_text(self) -> None:
        self.setText(self._code_to_label.get(self._current, self._current) + "  ▾")

    def set_value(self, code: str) -> None:
        """Установить выбор извне, без эмита сигнала."""
        if code == self._current or code not in self._code_to_label:
            return
        self._current = code
        self._refresh_text()

    def value(self) -> str:
        return self._current

    def _show_picker(self) -> None:
        if self._picker is not None:
            return
        picker = _LangPickerPopup(self._items, parent=None)
        picker.selected.connect(self._on_picker_selected)
        picker.closed.connect(self._on_picker_closed)
        self._picker = picker
        self.dropdown_opened.emit()
        anchor = self.mapToGlobal(QPoint(0, self.height()))
        picker.show_at(anchor, min_width=self.width())

    def _on_picker_selected(self, code: str) -> None:
        if code == self._current:
            return
        self._current = code
        self._refresh_text()
        self.value_changed.emit(code)

    def _on_picker_closed(self) -> None:
        picker = self._picker
        self._picker = None
        self.dropdown_closed.emit()
        if picker is not None:
            picker.deleteLater()
