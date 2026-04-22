from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .lang import POPULAR_LANGUAGES, language_display, normalize_lang_code
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
        layout.setContentsMargins(0, 0, 0, 0)
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
    _PROVIDER_ORDER = ("openrouter", "anthropic")

    def __init__(self, cfg: dict[str, Any], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки translato")
        self.setModal(True)

        layout = QVBoxLayout(self)

        active = cfg.get("active_provider", "openrouter")
        if active not in self._PROVIDER_ORDER:
            active = "openrouter"
        self._initial_active = active

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_provider_tab(cfg, active), "Провайдер")
        self._tabs.addTab(
            self._build_instruction_tab(cfg.get("custom_prompt", "")),
            "Инструкция",
        )
        self._tabs.addTab(
            self._build_languages_tab(cfg.get("preferred_dst_lang", "en")),
            "Языки",
        )
        layout.addWidget(self._tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.resize(540, self.sizeHint().height())

    def _build_provider_tab(self, cfg: dict[str, Any], active: str) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)

        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Провайдер:"))
        self._provider_combo = QComboBox()
        for pid in self._PROVIDER_ORDER:
            self._provider_combo.addItem(PROVIDER_LABELS[pid], pid)
        self._provider_combo.setCurrentIndex(self._PROVIDER_ORDER.index(active))
        selector_row.addWidget(self._provider_combo, 1)
        page_layout.addLayout(selector_row)

        self._active_label = QLabel()
        self._active_label.setTextFormat(Qt.TextFormat.RichText)
        self._active_label.setStyleSheet("padding: 6px 4px;")
        page_layout.addWidget(self._active_label)

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

        self._stack = QStackedWidget()
        self._stack.addWidget(self._openrouter_tab)
        self._stack.addWidget(self._anthropic_tab)
        self._stack.setCurrentIndex(self._PROVIDER_ORDER.index(active))

        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        page_layout.addWidget(self._stack)
        self._update_active_label()

        hint = QLabel(
            "Выбранный в списке провайдер становится активным после нажатия «OK». "
            "Ключи для обоих провайдеров хранятся независимо, можно держать оба."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        page_layout.addWidget(hint)

        return page

    def _build_languages_tab(self, current_code: str) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)

        title = QLabel("Язык перевода по умолчанию:")
        page_layout.addWidget(title)

        self._lang_combo = QComboBox()
        for code, name in POPULAR_LANGUAGES:
            self._lang_combo.addItem(language_display(code, name), code)
        normalized = normalize_lang_code(current_code, "en")
        idx = self._lang_combo.findData(normalized)
        if idx < 0:
            idx = 0
        self._lang_combo.setCurrentIndex(idx)
        page_layout.addWidget(self._lang_combo)

        hint = QLabel(
            "Этот язык будет использоваться как целевой при переводе. "
            "Если исходный текст уже на этом языке, перевод пойдёт в обратную сторону "
            "(между русским и английским). В окне перевода язык можно быстро сменить "
            "в выпадающем списке."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        page_layout.addWidget(hint)

        page_layout.addStretch(1)
        return page

    def _build_instruction_tab(self, current_value: str) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)

        title = QLabel("Дополнительная инструкция для модели:")
        page_layout.addWidget(title)

        self._prompt_edit = QPlainTextEdit(current_value)
        self._prompt_edit.setPlaceholderText(
            "Добавляется поверх основного промпта, не заменяет его.\n"
            "Например: «Используй формальный стиль» или «Термины из IT оставляй по-английски»."
        )
        self._prompt_edit.setMinimumHeight(180)
        page_layout.addWidget(self._prompt_edit, 1)

        hint = QLabel(
            "Инструкция применяется поверх системного промпта переводчика "
            "и не может его переопределить. Работает для обоих провайдеров."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        page_layout.addWidget(hint)

        return page

    def _on_provider_changed(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        self._update_active_label()

    def _update_active_label(self) -> None:
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
        data = self._provider_combo.currentData()
        if isinstance(data, str) and data in self._PROVIDER_ORDER:
            return data
        return "openrouter"

    def openrouter_model(self) -> str:
        return self._openrouter_tab.model_edit.text().strip()

    def openrouter_key(self) -> str:
        return self._openrouter_tab.key_edit.text().strip()

    def anthropic_model(self) -> str:
        return self._anthropic_tab.model_edit.text().strip()

    def anthropic_key(self) -> str:
        return self._anthropic_tab.key_edit.text().strip()

    def custom_prompt(self) -> str:
        return self._prompt_edit.toPlainText().strip()

    def preferred_dst_lang(self) -> str:
        data = self._lang_combo.currentData()
        if isinstance(data, str):
            return normalize_lang_code(data, "en")
        return "en"


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

        updates: dict[str, Any] = {
            "active_provider": dlg.active_provider(),
            "custom_prompt": dlg.custom_prompt(),
            "preferred_dst_lang": dlg.preferred_dst_lang(),
        }

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
