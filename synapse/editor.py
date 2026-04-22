from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QClipboard, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .i18n import t
from .lang import POPULAR_LANGUAGES, language_display, normalize_lang_code
from .lang_picker import LangPicker
from .tray import app_icon


class EditorWindow(QWidget):
    """Отдельное окно редактора переводов (Google-Translate-style).

    Обычное top-level окно: можно сворачивать, перекрывать, изменять размер.
    Автоперевод по debounce на вводе текста. Смена языков/swap — мгновенно.
    """

    # Сигналы наружу (в SynapseApp)
    translate_requested = Signal(str, str, str)  # (text, src, dst)
    closed = Signal()

    def __init__(
        self,
        *,
        default_width: int = 900,
        default_height: int = 520,
        debounce_ms: int = 500,
        preferred_src: str = "en",
        preferred_dst: str = "ru",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(t("editor.title"))
        self.setWindowIcon(app_icon())
        self.resize(default_width, default_height)
        self.setMinimumSize(540, 320)

        self._debounce_ms = int(debounce_ms)
        self._preferred_src = preferred_src
        self._preferred_dst = preferred_dst
        self._current_translation: str = ""
        self._streaming: bool = False

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._emit_translate)

        self._build_ui()
        self._apply_styles()
        self._wire_shortcuts()

    # --- UI -----------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Верхняя панель: src → swap → dst → (растяжка) → copy
        header = QHBoxLayout()
        header.setSpacing(6)

        lang_items = [(code, language_display(code, name)) for code, name in POPULAR_LANGUAGES]

        self._src_combo = LangPicker(lang_items)
        self._src_combo.setObjectName("langCombo")
        self._src_combo.set_value(self._preferred_src)
        self._src_combo.value_changed.connect(self._on_src_changed)
        header.addWidget(self._src_combo)

        self._swap_btn = QToolButton()
        self._swap_btn.setObjectName("swapBtn")
        self._swap_btn.setText("⇄")
        self._swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._swap_btn.setToolTip(t("editor.swap_tooltip"))
        self._swap_btn.setAutoRaise(True)
        self._swap_btn.clicked.connect(self._on_swap)
        header.addWidget(self._swap_btn)

        self._dst_combo = LangPicker(lang_items)
        self._dst_combo.setObjectName("langCombo")
        self._dst_combo.set_value(self._preferred_dst)
        self._dst_combo.value_changed.connect(self._on_dst_changed)
        header.addWidget(self._dst_combo)

        header.addStretch(1)

        self._copy_btn = QPushButton(t("popup.copy"))
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._copy_translation)
        header.addWidget(self._copy_btn)

        root.addLayout(header)

        # Сплиттер с двумя текстовыми полями
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(6)

        self._source_view = QPlainTextEdit()
        self._source_view.setObjectName("sourceView")
        self._source_view.setPlaceholderText(t("editor.source_placeholder"))
        self._source_view.textChanged.connect(self._on_source_changed)
        self._splitter.addWidget(self._source_view)

        self._translation_view = QPlainTextEdit()
        self._translation_view.setObjectName("translationView")
        self._translation_view.setReadOnly(True)
        self._translation_view.setPlaceholderText(t("editor.translation_placeholder"))
        self._splitter.addWidget(self._translation_view)

        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([450, 450])

        root.addWidget(self._splitter, 1)

        # Статусная строка
        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        root.addWidget(self._status)

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background: #1f2024;
                color: #f0f0f0;
            }
            QPlainTextEdit#sourceView,
            QPlainTextEdit#translationView {
                background: #2a2c31;
                color: #ffffff;
                border: 1px solid #3a3b40;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: #3a7afe;
                selection-color: #ffffff;
            }
            QPlainTextEdit#translationView {
                background: #262830;
            }
            QLabel#statusLabel {
                color: #9aa0a6;
                font-size: 11px;
                padding: 2px 4px;
            }
            QPushButton {
                background: #2c2e33; color: #e8e8e8;
                border: 1px solid #45474d; border-radius: 4px;
                padding: 4px 12px;
            }
            QPushButton:hover { background: #3a3c42; }
            QPushButton:pressed { background: #24262a; }
            QPushButton:disabled { color: #6a6d75; }
            QToolButton#langCombo {
                background: transparent;
                color: #c5c9cf;
                border: none;
                padding: 4px 8px;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QToolButton#langCombo:hover { color: #ffffff; }
            QToolButton#swapBtn {
                background: transparent;
                color: #9aa0a6;
                border: none;
                padding: 2px 6px;
                font-size: 16px;
            }
            QToolButton#swapBtn:hover { color: #ffffff; }
            QSplitter::handle { background: #1f2024; }
        """)

    def _wire_shortcuts(self) -> None:
        # Ctrl+Enter — мгновенный перевод без debounce.
        for seq in (QKeySequence("Ctrl+Return"), QKeySequence("Ctrl+Enter")):
            sc = QShortcut(seq, self)
            sc.activated.connect(self._emit_translate_now)

    # --- public API ---------------------------------------------------------

    def show_with(self, source_text: str, translation: str, src: str, dst: str) -> None:
        """Показать окно с заданным текстом. Если source_text непустой —
        триггерит немедленный перевод (без debounce)."""
        self._preferred_src = src
        self._preferred_dst = dst
        self._src_combo.set_value(src)
        self._dst_combo.set_value(dst)

        # Подставляем текст без повторного триггера debounce.
        self._source_view.blockSignals(True)
        self._source_view.setPlainText(source_text)
        self._source_view.blockSignals(False)

        self._current_translation = translation or ""
        self._translation_view.setPlainText(self._current_translation)
        self._copy_btn.setEnabled(bool(self._current_translation))

        self._show_and_focus()

        if source_text.strip():
            # Если есть текст — запускаем перевод сразу. Если уже есть перевод,
            # он останется видимым, новый пойдёт через soft-replace стриминг.
            self._emit_translate_now()

    def show_empty(self, src: str, dst: str) -> None:
        """Показать пустое окно."""
        self._preferred_src = src
        self._preferred_dst = dst
        self._src_combo.set_value(src)
        self._dst_combo.set_value(dst)
        self._source_view.blockSignals(True)
        self._source_view.clear()
        self._source_view.blockSignals(False)
        self._translation_view.clear()
        self._current_translation = ""
        self._copy_btn.setEnabled(False)
        self._status.setText("")
        self._show_and_focus()

    def _show_and_focus(self) -> None:
        if not self.isVisible():
            self.show()
        else:
            self.raise_()
            self.activateWindow()
        self._source_view.setFocus()

    def current_src(self) -> str:
        return self._src_combo.value()

    def current_dst(self) -> str:
        return self._dst_combo.value()

    # --- streaming callbacks (вызывает SynapseApp) ------------------------

    def begin_translation(self) -> None:
        self._streaming = True
        self._current_translation = ""
        self._translation_view.setPlainText("")
        self._copy_btn.setEnabled(False)
        self._status.setText(t("editor.translating"))

    def begin_soft_replace(self) -> None:
        """Старт перевода, но старый текст перевода остаётся до первого чанка."""
        self._streaming = True
        self._current_translation = ""
        self._copy_btn.setEnabled(False)
        self._status.setText(t("editor.translating"))

    def append_translation(self, delta: str) -> None:
        if not delta:
            return
        first_chunk = self._current_translation == ""
        self._streaming = True
        self._current_translation += delta
        self._translation_view.setPlainText(self._current_translation)
        if first_chunk:
            bar = self._translation_view.verticalScrollBar()
            if bar is not None:
                bar.setValue(0)
        self._copy_btn.setEnabled(True)

    def finish_translation(self) -> None:
        self._streaming = False
        self._status.setText(t("editor.ready"))

    def show_error(self, message: str) -> None:
        self._streaming = False
        self._translation_view.setPlainText(message)
        self._current_translation = ""
        self._copy_btn.setEnabled(False)
        self._status.setText("")

    # --- internal slots -----------------------------------------------------

    def _on_source_changed(self) -> None:
        text = self._source_view.toPlainText()
        if not text.strip():
            self._debounce.stop()
            self._translation_view.clear()
            self._current_translation = ""
            self._copy_btn.setEnabled(False)
            self._status.setText("")
            return
        self._debounce.start(self._debounce_ms)

    def _on_src_changed(self, code: str) -> None:
        new_src = normalize_lang_code(code, "en")
        if new_src == self._preferred_src:
            return
        self._preferred_src = new_src
        # Если src совпал с dst — инвертируем dst на разумный дефолт,
        # чтобы не переводить на тот же язык.
        if new_src == self._preferred_dst:
            self._preferred_dst = "ru" if new_src == "en" else "en"
            self._dst_combo.set_value(self._preferred_dst)
        self._emit_translate_now()

    def _on_dst_changed(self, code: str) -> None:
        new_dst = normalize_lang_code(code, "en")
        if new_dst == self._preferred_dst:
            return
        self._preferred_dst = new_dst
        if new_dst == self._preferred_src:
            self._preferred_src = "ru" if new_dst == "en" else "en"
            self._src_combo.set_value(self._preferred_src)
        self._emit_translate_now()

    def _on_swap(self) -> None:
        # Классический Google-Translate swap: меняем языки и переносим текущий
        # перевод в поле оригинала.
        new_src = self._preferred_dst
        new_dst = self._preferred_src
        self._preferred_src = new_src
        self._preferred_dst = new_dst
        self._src_combo.set_value(new_src)
        self._dst_combo.set_value(new_dst)

        if self._current_translation:
            self._source_view.blockSignals(True)
            self._source_view.setPlainText(self._current_translation)
            self._source_view.blockSignals(False)
            self._translation_view.clear()
            self._current_translation = ""
            self._copy_btn.setEnabled(False)
            self._emit_translate_now()
        elif self._source_view.toPlainText().strip():
            self._emit_translate_now()

    def _emit_translate(self) -> None:
        text = self._source_view.toPlainText()
        if not text.strip():
            return
        self.translate_requested.emit(text, self._preferred_src, self._preferred_dst)

    def _emit_translate_now(self) -> None:
        self._debounce.stop()
        self._emit_translate()

    def _copy_translation(self) -> None:
        if not self._current_translation:
            return
        cb = QApplication.clipboard()
        cb.setText(self._current_translation, QClipboard.Mode.Clipboard)
        original = t("popup.copy")
        self._copy_btn.setText(t("popup.copied"))
        QTimer.singleShot(1200, lambda: self._copy_btn.setText(original))

    # --- lifecycle ----------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        # Не уничтожаем окно — прячем и оповещаем, чтобы app мог сохранить
        # геометрию.
        self._debounce.stop()
        self.closed.emit()
        event.accept()
