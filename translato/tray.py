from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .providers.keys import (
    delete_anthropic_key,
    delete_openrouter_key,
    get_anthropic_key,
    get_openrouter_key,
    set_anthropic_key,
    set_openrouter_key,
)

PROVIDER_LABELS = {
    "openrouter": "OpenRouter",
    "anthropic": "Anthropic",
}


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


def _mask_key(key: str) -> str:
    """Показать начало и хвост ключа, середину скрыть."""
    if not key:
        return ""
    if len(key) <= 12:
        return key[:3] + "…"
    return f"{key[:10]}…{key[-4:]}"


class _ProviderTab(QWidget):
    def __init__(
        self,
        *,
        provider_id: str,
        link_html: str,
        model_value: str,
        key_placeholder: str,
        get_key: Callable[[], str | None],
        delete_key: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.provider_id = provider_id
        self._get_key = get_key
        self._delete_key = delete_key

        layout = QVBoxLayout(self)
        info = QLabel(link_html)
        info.setOpenExternalLinks(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        # Строка статуса: сохранён ли ключ, его маска.
        self.status_label = QLabel()
        self.status_label.setTextFormat(Qt.TextFormat.RichText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        form = QFormLayout()
        self.model_edit = QLineEdit(model_value)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText(key_placeholder)
        form.addRow("Модель:", self.model_edit)
        form.addRow("Новый ключ:", self.key_edit)
        layout.addLayout(form)

        row = QHBoxLayout()
        row.addStretch(1)
        self.delete_btn = QPushButton("Удалить сохранённый ключ")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        row.addWidget(self.delete_btn)
        layout.addLayout(row)

        layout.addStretch(1)

        self._refresh_status()

    def _refresh_status(self) -> None:
        key = self._get_key()
        if key:
            self.status_label.setText(
                f'<span style="color:#2e7d32;">● Ключ сохранён:</span> '
                f'<code>{_mask_key(key)}</code>'
            )
            self.delete_btn.setEnabled(True)
            self.key_edit.setPlaceholderText("(введите, чтобы заменить сохранённый ключ)")
        else:
            self.status_label.setText(
                '<span style="color:#c62828;">● Ключ не задан</span>'
            )
            self.delete_btn.setEnabled(False)

    def _on_delete_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "translato",
            f"Удалить сохранённый ключ {PROVIDER_LABELS.get(self.provider_id, self.provider_id)} "
            "из Windows Credential Manager?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._delete_key()
        self.key_edit.clear()
        self._refresh_status()


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки translato")
        self.setModal(True)

        layout = QVBoxLayout(self)

        self._active_label = QLabel()
        self._active_label.setTextFormat(Qt.TextFormat.RichText)
        self._active_label.setStyleSheet("padding: 6px 4px;")
        layout.addWidget(self._active_label)

        self._tabs = QTabWidget()

        self._openrouter_tab = _ProviderTab(
            provider_id="openrouter",
            link_html='Ключ OpenRouter: <a href="https://openrouter.ai/keys">openrouter.ai/keys</a>',
            model_value=cfg["openrouter"]["model"],
            key_placeholder="sk-or-v1-…",
            get_key=get_openrouter_key,
            delete_key=delete_openrouter_key,
        )
        self._anthropic_tab = _ProviderTab(
            provider_id="anthropic",
            link_html='Ключ Anthropic: <a href="https://console.anthropic.com/settings/keys">'
                      'console.anthropic.com/settings/keys</a>',
            model_value=cfg["anthropic"]["model"],
            key_placeholder="sk-ant-…",
            get_key=get_anthropic_key,
            delete_key=delete_anthropic_key,
        )

        self._tabs.addTab(self._openrouter_tab, "OpenRouter")
        self._tabs.addTab(self._anthropic_tab, "Anthropic")

        active = cfg.get("active_provider", "openrouter")
        self._initial_active = active
        self._tabs.setCurrentIndex(1 if active == "anthropic" else 0)
        self._tabs.currentChanged.connect(self._update_active_label)
        self._update_tab_titles()
        self._update_active_label(self._tabs.currentIndex())

        layout.addWidget(self._tabs)

        hint = QLabel(
            "Активным становится провайдер той вкладки, на которой вы нажмёте «OK». "
            "Ключи для обеих вкладок хранятся независимо, можно держать оба."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.resize(500, self.sizeHint().height())

    def _update_tab_titles(self) -> None:
        # Метка «(активный)» остаётся у вкладки, которая была активна при открытии
        # диалога — чтобы пользователь видел текущее состояние системы,
        # а не то, что он прямо сейчас выбрал вкладкой.
        for idx, pid in ((0, "openrouter"), (1, "anthropic")):
            base = PROVIDER_LABELS[pid]
            if pid == self._initial_active:
                self._tabs.setTabText(idx, f"● {base} (активный)")
            else:
                self._tabs.setTabText(idx, base)

    def _update_active_label(self, _idx: int) -> None:
        selected = self.active_provider()
        selected_name = PROVIDER_LABELS[selected]
        initial_name = PROVIDER_LABELS[self._initial_active]
        if selected == self._initial_active:
            self._active_label.setText(
                f'Сейчас используется: <b>{initial_name}</b>'
            )
        else:
            self._active_label.setText(
                f'Сейчас используется: <b>{initial_name}</b>. '
                f'После «OK» переключится на <b>{selected_name}</b>.'
            )

    def active_provider(self) -> str:
        return "anthropic" if self._tabs.currentIndex() == 1 else "openrouter"

    def openrouter_model(self) -> str:
        return self._openrouter_tab.model_edit.text().strip()

    def openrouter_key(self) -> str:
        return self._openrouter_tab.key_edit.text().strip()

    def anthropic_model(self) -> str:
        return self._anthropic_tab.model_edit.text().strip()

    def anthropic_key(self) -> str:
        return self._anthropic_tab.key_edit.text().strip()


class TrayController:
    def __init__(
        self,
        icon: QIcon,
        get_config: Callable[[], dict[str, Any]],
        on_config_saved: Callable[[dict[str, Any]], None],
        on_pause_toggled: Callable[[bool], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._get_config = get_config
        self._on_config_saved = on_config_saved
        self._on_pause_toggled = on_pause_toggled
        self._on_quit = on_quit
        self._paused = False

        self.tray = QSystemTrayIcon(icon)
        self.tray.activated.connect(self._on_activated)

        self._menu = QMenu()
        self._pause_action = QAction("Пауза", self._menu)
        self._pause_action.triggered.connect(self._toggle_pause)
        self._menu.addAction(self._pause_action)

        self._provider_action = QAction(self._menu)
        self._provider_action.setEnabled(False)  # информационная строка
        self._menu.addAction(self._provider_action)

        settings_action = QAction("Настройки…", self._menu)
        settings_action.triggered.connect(self.open_settings)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()
        quit_action = QAction("Выход", self._menu)
        quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(quit_action)

        self.tray.setContextMenu(self._menu)
        self._refresh_provider_indicator()
        self.tray.show()

    def _refresh_provider_indicator(self) -> None:
        cfg = self._get_config()
        pid = cfg.get("active_provider", "openrouter")
        name = PROVIDER_LABELS.get(pid, pid)
        has_key = bool(get_anthropic_key()) if pid == "anthropic" else bool(get_openrouter_key())
        key_mark = "✓" if has_key else "⚠ без ключа"
        self._provider_action.setText(f"Провайдер: {name}  [{key_mark}]")
        paused_suffix = " — пауза" if self._paused else ""
        self.tray.setToolTip(f"translato — {name}{paused_suffix}")

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_settings()

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._pause_action.setText("Продолжить" if self._paused else "Пауза")
        self._on_pause_toggled(self._paused)
        self._refresh_provider_indicator()

    def open_settings(self) -> bool:
        cfg = self._get_config()
        dlg = SettingsDialog(cfg=cfg)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            # Ключ мог быть удалён через кнопку внутри диалога — обновим индикатор.
            self._refresh_provider_indicator()
            return False

        updates: dict[str, Any] = {"active_provider": dlg.active_provider()}

        or_model = dlg.openrouter_model()
        if or_model:
            updates["openrouter"] = {"model": or_model}
        or_key = dlg.openrouter_key()
        if or_key:
            try:
                set_openrouter_key(or_key)
            except ValueError as e:
                QMessageBox.warning(None, "translato — ключ OpenRouter", str(e))
                return False

        an_model = dlg.anthropic_model()
        if an_model:
            updates["anthropic"] = {"model": an_model}
        an_key = dlg.anthropic_key()
        if an_key:
            try:
                set_anthropic_key(an_key)
            except ValueError as e:
                QMessageBox.warning(None, "translato — ключ Anthropic", str(e))
                return False

        self._on_config_saved(updates)
        self._refresh_provider_indicator()
        return True

    def notify(self, title: str, message: str) -> None:
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

    @staticmethod
    def warn_missing_tray() -> None:
        QMessageBox.critical(
            None,
            "translato",
            "Системный трей недоступен в этой системе.",
        )
