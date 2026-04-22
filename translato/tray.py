from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QLabel,
)

from .providers.openrouter import get_api_key, set_api_key


def make_tray_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#3a7afe"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(4, 4, 56, 56, 12, 12)
    p.setPen(QColor("white"))
    font = p.font()
    font.setBold(True)
    font.setPointSize(26)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    p.end()
    return QIcon(pm)


class SettingsDialog(QDialog):
    def __init__(self, current_model: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки translato")
        self.setModal(True)

        layout = QVBoxLayout(self)

        info = QLabel(
            'Ключ OpenRouter: <a href="https://openrouter.ai/keys">openrouter.ai/keys</a>'
        )
        info.setOpenExternalLinks(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        form = QFormLayout()
        self._model_edit = QLineEdit(current_model)
        self._key_edit = QLineEdit()
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setPlaceholderText("sk-or-v1-…")
        existing = get_api_key()
        if existing:
            self._key_edit.setPlaceholderText("(ключ сохранён — введите новый, чтобы заменить)")
        form.addRow("Модель:", self._model_edit)
        form.addRow("API-ключ:", self._key_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.resize(420, self.sizeHint().height())

    def model_value(self) -> str:
        return self._model_edit.text().strip()

    def api_key_value(self) -> str:
        return self._key_edit.text().strip()


class TrayController:
    def __init__(
        self,
        icon: QIcon,
        get_model: Callable[[], str],
        set_model: Callable[[str], None],
        on_pause_toggled: Callable[[bool], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._get_model = get_model
        self._set_model = set_model
        self._on_pause_toggled = on_pause_toggled
        self._on_quit = on_quit
        self._paused = False

        self.tray = QSystemTrayIcon(icon)
        self.tray.setToolTip("translato — переводчик")
        self.tray.activated.connect(self._on_activated)

        self._menu = QMenu()
        self._pause_action = QAction("Пауза", self._menu)
        self._pause_action.triggered.connect(self._toggle_pause)
        self._menu.addAction(self._pause_action)

        settings_action = QAction("Настройки…", self._menu)
        settings_action.triggered.connect(self.open_settings)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()
        quit_action = QAction("Выход", self._menu)
        quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(quit_action)

        self.tray.setContextMenu(self._menu)
        self.tray.show()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._pause_action.setText("Продолжить" if self._paused else "Пауза")
        self._on_pause_toggled(self._paused)
        self.tray.setToolTip("translato — пауза" if self._paused else "translato — переводчик")

    def open_settings(self) -> bool:
        dlg = SettingsDialog(current_model=self._get_model())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_model = dlg.model_value()
            if new_model:
                self._set_model(new_model)
            new_key = dlg.api_key_value()
            if new_key:
                try:
                    set_api_key(new_key)
                except ValueError as e:
                    QMessageBox.warning(None, "translato — ключ", str(e))
                    return False
            return True
        return False

    def notify(self, title: str, message: str) -> None:
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    @staticmethod
    def warn_missing_tray() -> None:
        QMessageBox.critical(
            None,
            "translato",
            "Системный трей недоступен в этой системе.",
        )
