"""Preferences, syntax, spelling and isolated recoverable editor sessions."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from PyQt6.QtCore import QLockFile, QPoint, QRectF, QStandardPaths, Qt, QTimer, QFile
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFontComboBox, QFormLayout, QGridLayout, QLabel, QMenu, QInputDialog,
    QMessageBox, QPushButton, QTabWidget, QToolButton, QHBoxLayout, QVBoxLayout, QWidget,
)
from PyQt6.Qsci import QsciLexerBash, QsciLexerMarkdown
from editor import Editor, Tabs, Window, STYLE

# GTK's standard chooser palette, arranged in the same columns as Ptyxis-tc.
# Preserve the original five rows and prepend a softer tint of the top row.
TAB_COLOR_ROWS = (
    ("#99c1f1", "#8ff0a4", "#f9f06b", "#ffbe6f", "#f66151", "#dc8add", "#cdab8f", "#ffffff", "#77767b"),
    ("#62a0ea", "#57e389", "#f8e45c", "#ffa348", "#ed333b", "#c061cb", "#b5835a", "#f6f5f4", "#5e5c64"),
    ("#3584e4", "#33d17a", "#f6d32d", "#ff7800", "#e01b24", "#9141ac", "#986a44", "#deddda", "#3d3846"),
    ("#1c71d8", "#2ec27e", "#f5c211", "#e66100", "#c01c28", "#813d9c", "#865e3c", "#c0bfbc", "#241f31"),
    ("#1a5fb4", "#26a269", "#e5a50a", "#c64600", "#a51d2d", "#613583", "#63452c", "#9a9996", "#000000"),
)

def tab_color_palette():
    lighter = [QColor(*(round(channel + (255 - channel) * 0.5)
                       for channel in QColor(value).getRgb()[:3])).name()
               for value in TAB_COLOR_ROWS[0]]
    return [lighter, *[list(row) for row in TAB_COLOR_ROWS]]

class TabColorDialog(QDialog):
    def __init__(self, initial, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tab Background Color")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setObjectName("tabColorChooser")
        self.setStyleSheet("""
            QDialog#tabColorChooser { background: #e8e8e8; border: 1px solid #38383c; border-radius: 14px; }
            QDialog#tabColorChooser QLabel { color: #202020; background: transparent; border: none; font-size: 18px; }
            QDialog#tabColorChooser QPushButton { padding: 0; margin: 0; }
            QPushButton#chooserCancel, QPushButton#chooserSelect {
                color: white; background: #38383c; border: none; border-radius: 9px;
                font-size: 18px; font-weight: bold;
            }
            QPushButton#chooserSelect { background: #3584e4; }
            QPushButton#chooserCancel:hover { background: #48484c; }
            QPushButton#chooserSelect:hover { background: #4992e8; }
        """)
        self.selected_color = QColor(initial)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(12)
        header = QHBoxLayout()
        header.setSpacing(8)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("chooserCancel")
        cancel.setFixedSize(96, 34)
        cancel.clicked.connect(self.reject)
        header.addWidget(cancel)
        title = QLabel("Tab Background Color")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold;")
        header.addWidget(title, 1)
        select = QPushButton("Select")
        select.setObjectName("chooserSelect")
        select.setFixedSize(96, 34)
        select.setDefault(True)
        select.clicked.connect(self.accept)
        header.addWidget(select)
        layout.addLayout(header)
        grid = QGridLayout()
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(2)
        self.swatches = []
        palette = tab_color_palette()
        for row, colors in enumerate(palette):
            for column, value in enumerate(colors):
                button = self.make_swatch(value)
                button.setProperty("roundedTop", row == 0)
                button.setProperty("roundedBottom", row == len(palette) - 1)
                grid.addWidget(button, row, column)
        layout.addLayout(grid)
        layout.addWidget(QLabel("Custom"))
        custom_row = QHBoxLayout()
        custom_row.setSpacing(4)
        custom = QPushButton("+")
        custom.setAccessibleName("Add custom color")
        custom.setFixedSize(48, 34)
        custom.setStyleSheet("QPushButton { background: #38383c; color: white; border: none; border-top-left-radius: 10px; border-bottom-left-radius: 10px; font-size: 28px; }")
        custom.clicked.connect(self.custom_color)
        custom_row.addWidget(custom)
        self.custom_swatches = []
        for value in ("#141414", "#f6f5f4", "#e5e5e5", "#c0c0c0"):
            button = self.make_swatch(value)
            self.custom_swatches.append(button)
            custom_row.addWidget(button)
        self.custom_swatches[-1].setProperty("roundedRight", True)
        custom_row.addStretch()
        layout.addLayout(custom_row)
        self.select_color(initial)
        self.setFixedSize(self.sizeHint())

    def make_swatch(self, value):
        button = QPushButton()
        button.setFixedSize(48, 32)
        button.setCheckable(True)
        button.setAutoDefault(False)
        button.setToolTip(value)
        button.setAccessibleName("Choose color " + value)
        button.setProperty("swatchColor", value)
        button.clicked.connect(lambda checked=False, b=button: self.select_color(QColor(b.property("swatchColor"))))
        self.swatches.append(button)
        return button

    def select_color(self, color):
        self.selected_color = QColor(color)
        value = self.selected_color.name()
        # An arbitrary existing color remains visible and selectable in Custom.
        if value not in [b.property("swatchColor") for b in self.swatches]:
            self.custom_swatches[0].setProperty("swatchColor", value)
            self.custom_swatches[0].setToolTip(value)
            self.custom_swatches[0].setAccessibleName("Choose color " + value)
        selected_once = False
        for button in self.swatches:
            swatch = button.property("swatchColor")
            selected = swatch == value and not selected_once
            selected_once |= selected
            button.setChecked(selected)
            button.setText("✓" if selected else "")
            ink = "#202020" if QColor(swatch).lightness() > 150 else "#ffffff"
            corners = "border-radius: 0;"
            if button.property("roundedTop"):
                corners += "border-top-left-radius: 10px; border-top-right-radius: 10px;"
            if button.property("roundedBottom"):
                corners += "border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;"
            if button.property("roundedRight"):
                corners += "border-top-right-radius: 10px; border-bottom-right-radius: 10px;"
            button.setStyleSheet(f"QPushButton {{ background: {swatch}; color: {ink}; border: none; {corners} font-size: 20px; }} QPushButton:focus {{ border: 2px solid {ink}; }}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 48:
            if self.windowHandle():
                self.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def custom_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Custom Tab Color",
                                     QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid():
            self.select_color(color)


def choose_editor_color(initial, parent):
    dialog = TabColorDialog(initial, parent)
    return dialog.selected_color if dialog.exec() == QDialog.DialogCode.Accepted else QColor()

ICON_CACHE = {}

def tab_icon(name, color):
    key = (name, color)
    if key not in ICON_CACHE:
        from PyQt6.QtSvg import QSvgRenderer
        source = (Path(__file__).parent / "icons" / (name + ".svg")).read_bytes()
        source = source.replace(b"#333", color.encode()).replace(b"#555", color.encode())
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        QSvgRenderer(source).render(painter)
        painter.end()
        ICON_CACHE[key] = QIcon(pixmap)
    return ICON_CACHE[key]


DEFAULTS = dict(interface_font="System", interface_px=15.3, tab_px=15.3,
                sidebar_px=17.85, editor_font="System Monospace", editor_pt=10.8,
                tab_width=2, spaces=False, spell=False, spell_language="en_US",
                prompt_on_close=False, active_color="#e8e8e8", inactive_color="#f8f8f8", show_git=True, syntax=True, show_welcome=True)


def atomic_json(path: Path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    data = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_document(record):
    if not isinstance(record, dict) or not isinstance(record.get("text"), str) or not isinstance(record.get("title"), str):
        raise ValueError("Invalid recovered document; the original snapshot has been preserved.")
    if record.get("path") is not None and not isinstance(record["path"], str):
        raise ValueError("Invalid recovered document path.")
    for key in ("modified", "pinned", "spaces"):
        if key in record and not isinstance(record[key], bool):
            raise ValueError("Invalid recovered document option.")
    if record.get("tab_width", 2) not in (2, 4, 8) or record.get("eol", 2) not in (0, 1, 2):
        raise ValueError("Invalid recovered tab width or line ending.")
    for key, length in (("cursor", 2), ("selection", 4)):
        if key in record and (not isinstance(record[key], list) or len(record[key]) != length or any(not isinstance(value, int) for value in record[key])):
            raise ValueError("Invalid recovered cursor or selection.")
    for key in ("bom", "disk"):
        if record.get(key) is not None:
            try:
                base64.b64decode(record[key], validate=True)
            except (ValueError, TypeError) as error:
                raise ValueError("Invalid recovered byte data.") from error
    if record.get("encoding", "utf-8") not in ("utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be", "cp1252", "mac_roman"):
        raise ValueError("Invalid recovered encoding.")
    if record.get("language") not in (None, "Plain Text", "Bash", "Markdown"):
        raise ValueError("Invalid recovered language.")
    for key in ("scroll", "horizontal"):
        if key in record and (not isinstance(record[key], int) or record[key] < 0):
            raise ValueError("Invalid recovered scroll position.")
    if not isinstance(record.get("ignored_words", []), list) or any(not isinstance(word, str) for word in record.get("ignored_words", [])):
        raise ValueError("Invalid ignored spelling words.")
    return record


def read_session(path):
    record = json.loads(path.read_text())
    if not isinstance(record, dict) or record.get("version") != 1 or not isinstance(record.get("documents"), list):
        raise ValueError("Invalid recovery snapshot.")
    for document in record["documents"]:
        validate_document(document)
    if not isinstance(record.get("active", 0), int) or (record.get("workspace") is not None and not isinstance(record["workspace"], str)):
        raise ValueError("Invalid recovery session metadata.")
    identity = record.get("identity")
    if identity is not None and (not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity)):
        raise ValueError("Invalid recovery window identity.")
    return record


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.settings = dict(DEFAULTS)
        preferences = self.root / "preferences.json"
        if preferences.exists():
            values = json.loads(preferences.read_text())
            if not isinstance(values, dict):
                raise ValueError("Preferences are not a JSON object.")
            self.settings.update({key: value for key, value in values.items() if key in DEFAULTS})
        self.validate_settings(self.settings)

    @staticmethod
    def validate_settings(values):
        for key in ("interface_px", "tab_px", "sidebar_px", "editor_pt"):
            if not isinstance(values[key], (int, float)) or not 8 <= values[key] <= 48:
                raise ValueError(f"Invalid font size: {key}")
        if values["tab_width"] not in (2, 4, 8):
            raise ValueError("Invalid tab width")
        for key in ("active_color", "inactive_color"):
            if not QColor(values[key]).isValid():
                raise ValueError("Invalid tab color")

    def save_settings(self, values):
        self.validate_settings(values)
        atomic_json(self.root / "preferences.json", values)
        self.settings = dict(values)

    def window_path(self, identity):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", identity):
            raise ValueError("Invalid window identity")
        return self.root / "windows" / f"{identity}.json"

    def folder_path(self, identity, workspace):
        self.window_path(identity)
        key = hashlib.sha256(str(workspace or "loose-documents").encode()).hexdigest()
        return self.root / "folders" / (identity if workspace is None else "shared") / f"{key}.json"

    def save(self, path, record):
        if path.exists():
            try:
                old = read_session(path)
            except (OSError, ValueError):
                # Preserve corrupt originals before replacing them.
                atomic_json(path.with_name(path.stem + ".corrupt-" + uuid.uuid4().hex + ".json"), {"raw": base64.b64encode(path.read_bytes()).decode()})
            else:
                if old == record:
                    return
                atomic_json(path.with_suffix(".previous.json"), old)
        atomic_json(path, record)

    def load(self, path):
        if not path.exists():
            return None
        try:
            return read_session(path)
        except (OSError, ValueError) as error:
            previous = path.with_suffix(".previous.json")
            if previous.exists():
                return read_session(previous)
            raise ValueError(f"Could not restore {path.name}: {error}") from error

    def archive(self, record):
        validate_document(record)
        path = self.root / "closed-tabs" / f"{uuid.uuid4().hex}.json"
        atomic_json(path, record)
        return path

    def recent(self):
        path = self.root / "recent.json"
        if not path.exists():
            return []
        values = json.loads(path.read_text())
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError("Invalid recent-items history.")
        return [Path(value) for value in values]


class EnhancedEditor(Editor):
    def __init__(self, options):
        super().__init__()
        self.options = options
        self.insert_spaces = bool(options["spaces"])
        self.setTabWidth(options["tab_width"])
        self.language_name = "Plain Text"
        self.language_override = None
        self.tab_color = None
        self.syntax_lexer = None
        self.ignored_words = set()
        self.misspellings = []
        self.spell_click = None
        self.spell_indicator = self.indicatorDefine(self.IndicatorStyle.SquiggleIndicator, 12)
        self.setIndicatorForegroundColor(QColor("#c01c28"), self.spell_indicator)
        self.dictionary = None
        self.spelling_available = False
        try:
            import enchant
            self.dictionary = enchant.Dict(options["spell_language"])
            self.spelling_available = True
        except Exception as error:
            self.spelling_error = str(error)
        self.spell_timer = QTimer(self)
        self.spell_timer.setSingleShot(True)
        self.spell_timer.setInterval(350)
        self.spell_timer.timeout.connect(self.check_spelling)
        self.textChanged.connect(self.schedule_spelling)

    def mousePressEvent(self, event):
        self.spell_click = event.position().toPoint() if event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.NoModifier else None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.spell_click is None or event.button() != Qt.MouseButton.LeftButton or event.modifiers() != Qt.KeyboardModifier.NoModifier:
            return
        origin, self.spell_click = self.spell_click, None
        if (origin - event.position().toPoint()).manhattanLength() > 3:
            return
        self.check_spelling()
        # Normal mouse handling has placed the caret; both positions use UTF-8 bytes.
        position = self.SendScintilla(self.SCI_GETCURRENTPOS)
        record = next((value for value in self.misspellings if value[0] < position < value[1]), None)
        if record:
            menu = self.correction_menu(record)
            self.spell_menu = menu
            menu.popup(event.globalPosition().toPoint())

    def correction_menu(self, record):
        menu = QMenu(self)
        suggestions = self.dictionary.suggest(record[2].replace("’", "'"))[:8] if self.dictionary else []
        for suggestion in suggestions:
            menu.addAction(suggestion, lambda checked=False, replacement=suggestion: self.correct_spelling(record, replacement))
        if not suggestions:
            menu.addAction("No suggestions").setEnabled(False)
        menu.addSeparator()
        menu.addAction("× Ignore", lambda: self.ignore_spelling(record[2]))
        menu.aboutToHide.connect(menu.deleteLater)
        return menu

    def correct_spelling(self, record, replacement):
        start, end, original = record
        if self.text().encode("utf-8")[start:end].decode("utf-8", errors="replace") != original:
            return
        data = replacement.encode("utf-8")
        self.beginUndoAction()
        try:
            self.SendScintilla(self.SCI_SETTARGETSTART, start)
            self.SendScintilla(self.SCI_SETTARGETEND, end)
            self.SendScintilla(self.SCI_REPLACETARGET, len(data), data)
            self.SendScintilla(self.SCI_SETEMPTYSELECTION, start + len(data))
        finally:
            self.endUndoAction()
        self.check_spelling()

    def ignore_spelling(self, word):
        self.ignored_words.add(word.casefold())
        self.check_spelling()
        if hasattr(self.window(), "schedule_recovery"):
            self.window().schedule_recovery()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if self.insert_spaces:
                position = self.SendScintilla(self.SCI_GETSELECTIONSTART)
                column = self.SendScintilla(self.SCI_GETCOLUMN, position)
                if self.SendScintilla(self.SCI_SELECTIONISRECTANGLE):
                    anchor = self.SendScintilla(self.SCI_GETRECTANGULARSELECTIONANCHOR)
                    caret = self.SendScintilla(self.SCI_GETRECTANGULARSELECTIONCARET)
                    column = min(self.SendScintilla(self.SCI_GETCOLUMN, anchor) + self.SendScintilla(self.SCI_GETRECTANGULARSELECTIONANCHORVIRTUALSPACE), self.SendScintilla(self.SCI_GETCOLUMN, caret) + self.SendScintilla(self.SCI_GETRECTANGULARSELECTIONCARETVIRTUALSPACE))
                width = self.tabWidth() - column % self.tabWidth()
                if self.SendScintilla(self.SCI_GETSELECTIONS) > 1:
                    self.paste(" " * width)
                else:
                    self.replaceSelectedText(" " * width)
                event.accept()
                return
        super().keyPressEvent(event)

    def load(self, path):
        super().load(path)
        self.configure_language()

    def configure_language(self, selected=None):
        if selected is not None:
            self.language_override = None if selected == "Automatic" else selected
        extension = self.path.suffix.lower() if self.path else ""
        inferred = "Bash" if extension in (".sh", ".bash") or self.text().startswith(("#!/bin/bash", "#!/usr/bin/env bash", "#!/bin/sh")) else "Markdown" if extension in (".md", ".markdown") else "Plain Text"
        self.language_name = self.language_override or inferred
        previous = self.syntax_lexer
        self.syntax_lexer = QsciLexerBash(self) if self.language_name == "Bash" else QsciLexerMarkdown(self) if self.language_name == "Markdown" else None
        self.setLexer(self.syntax_lexer)
        if self.syntax_lexer:
            self.syntax_lexer.setDefaultFont(self.font())
            self.syntax_lexer.setFont(self.font())
            self.syntax_lexer.setPaper(QColor("white"))
            self.syntax_lexer.setColor(QColor("#202020"))
            if self.language_name == "Bash":
                # Xcode's installed Default (Light) Swift token colors, mapped to Bash.
                self.syntax_lexer.setColor(QColor("#262626"))
                for style, color in [(QsciLexerBash.Comment, "#5d6c79"), (QsciLexerBash.Keyword, "#9b2393"), (QsciLexerBash.DoubleQuotedString, "#c41a16"), (QsciLexerBash.SingleQuotedString, "#c41a16"), (QsciLexerBash.Scalar, "#326d74"), (QsciLexerBash.Number, "#1c00cf"), (QsciLexerBash.Backticks, "#6c36a9"), (QsciLexerBash.HereDocumentDelimiter, "#c41a16"), (QsciLexerBash.SingleQuotedHereDocument, "#c41a16")]:
                    self.syntax_lexer.setColor(QColor(color), style)
            else:
                for style in range(1, 22):
                    self.syntax_lexer.setColor(QColor("#75507b" if style <= 7 else "#204a87"), style)
            if not self.options.get("syntax", True):
                self.syntax_lexer.setColor(QColor("#202020"))
        if previous:
            previous.deleteLater()
        self.schedule_spelling()

    def apply_font(self, font):
        self.setFont(font)
        self.setMarginsFont(font)
        if self.syntax_lexer:
            self.syntax_lexer.setDefaultFont(font)
            self.syntax_lexer.setFont(font)

    def schedule_spelling(self):
        self.spell_timer.start()

    def check_spelling(self):
        self.misspellings = []
        self.clearIndicatorRange(0, 0, self.lines(), 0, self.spell_indicator)
        if not self.options["spell"] or self.dictionary is None:
            return
        text = self.text()
        self.SendScintilla(self.SCI_COLOURISE, 0, -1)
        encoded_offset = 0
        fenced = False
        for line_number, line in enumerate(text.splitlines(keepends=True)):
            if self.language_name == "Markdown" and line.lstrip().startswith(("```", "~~~")):
                fenced = not fenced
                encoded_offset += len(line.encode("utf-8"))
                continue
            if fenced:
                encoded_offset += len(line.encode("utf-8"))
                continue
            urls = [(match.start(), match.end()) for match in re.finditer(r"(?:https?://|www\.)\S+", line)]
            for word in re.finditer(r"[^\W\d_]+(?:['’][^\W\d_]+)?", line):
                if any(begin <= word.start() < end for begin, end in urls):
                    continue
                start = encoded_offset + len(line[:word.start()].encode("utf-8"))
                if self.language_name == "Bash" and self.SendScintilla(self.SCI_GETSTYLEAT, start) != QsciLexerBash.Comment:
                    continue
                # Ignore Markdown inline code and links/URLs; do not change file text.
                if self.language_name == "Markdown" and (line[:word.start()].count("`") % 2 or "http" in word.group().lower()):
                    continue
                if word.group().casefold() not in self.ignored_words and not self.dictionary.check(word.group().replace("’", "'")):
                    self.misspellings.append((start, start + len(word.group().encode("utf-8")), word.group()))
                    self.SendScintilla(self.SCI_SETINDICATORCURRENT, self.spell_indicator)
                    self.SendScintilla(self.SCI_INDICATORFILLRANGE, start, len(word.group().encode("utf-8")))
            encoded_offset += len(line.encode("utf-8"))


class ColorTabs(Tabs):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setHeight(34)
        return size

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())
        for index in range(self.count()):
            rect = self.tabRect(index).adjusted(1, 3, -1, 0)
            editor = self.window.tabs.widget(index)
            active = index == self.currentIndex()
            color = editor.tab_color or self.window.options["active_color" if active else "inactive_color"]
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor("#bcbcbc")))
            painter.drawRoundedRect(QRectF(rect), 5, 5)
            if active:
                painter.fillRect(rect.left(), rect.bottom() - 2, rect.width(), 3, QColor("#3584e4"))
            luminance = QColor(color).lightness()
            painter.setPen(QColor("#202020" if luminance > 115 else "#ffffff"))
            text_rect = rect.adjusted(16, 0, -62, -3)
            label = painter.fontMetrics().elidedText(self.tabText(index), Qt.TextElideMode.ElideRight, text_rect.width())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, label)


class Preferences(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.setWindowTitle("nex-editg Preferences")
        self.resize(540, 400)
        self.values = dict(owner.options)
        layout = QVBoxLayout(self)
        sections = QTabWidget()
        layout.addWidget(sections)
        self.fields = {}
        for title in ("Fonts", "Editing", "Appearance", "Spelling"):
            page = QWidget()
            form = QFormLayout(page)
            sections.addTab(page, title)
            if title == "Fonts":
                system = QCheckBox("Use system interface font")
                system.setChecked(self.values["interface_font"] == "System")
                self.fields["system"] = system
                form.addRow(system)
                editor_system = QCheckBox("Use system monospace editor font")
                editor_system.setChecked(self.values["editor_font"] == "System Monospace")
                self.fields["editor_system"] = editor_system
                form.addRow(editor_system)
                for key, label in [("interface_font", "Interface font"), ("editor_font", "Editor font")]:
                    field = QFontComboBox()
                    if key == "editor_font":
                        field.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
                    chosen = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont) if self.values[key] == "System Monospace" else QFont(self.values[key] if self.values[key] != "System" else QApplication.font().family())
                    field.setCurrentFont(chosen)
                    self.fields[key] = field
                    form.addRow(label, field)
                self.fields["interface_font"].setEnabled(not system.isChecked())
                system.toggled.connect(lambda checked: self.fields["interface_font"].setEnabled(not checked))
                self.fields["editor_font"].setEnabled(not editor_system.isChecked())
                editor_system.toggled.connect(lambda checked: self.fields["editor_font"].setEnabled(not checked))
                for key, label in [("interface_px", "Interface size (px)"), ("tab_px", "Tab title size (px)"), ("sidebar_px", "Sidebar size (px)"), ("editor_pt", "Editor size (pt)")]:
                    field = QDoubleSpinBox()
                    field.setRange(8, 48)
                    field.setSingleStep(0.5)
                    field.setValue(self.values[key])
                    self.fields[key] = field
                    form.addRow(label, field)
            elif title == "Editing":
                width = QComboBox()
                width.addItems(["2", "4", "8"])
                width.setCurrentText(str(self.values["tab_width"]))
                self.fields["tab_width"] = width
                form.addRow("Default tab width", width)
                for key, label in [("spaces", "Insert spaces instead of tabs"), ("prompt_on_close", "Ask to save when closing the app (recovery is always kept)")]:
                    field = QCheckBox(label)
                    field.setChecked(self.values[key])
                    self.fields[key] = field
                    form.addRow(field)
                form.addRow(QLabel("Bottom controls change the current document.\nPreferences set defaults for new documents."))
                git = QCheckBox("Show Git status in sidebar")
                git.setChecked(self.values["show_git"])
                self.fields["show_git"] = git
                form.addRow(git)
                syntax = QCheckBox("Enable syntax highlighting")
                syntax.setChecked(self.values["syntax"])
                self.fields["syntax"] = syntax
                form.addRow(syntax)
                form.addRow(QLabel("One fixed scheme; Bash uses Xcode Default Light colors."))
            elif title == "Appearance":
                welcome = QCheckBox("Show Welcome on startup")
                welcome.setChecked(self.values["show_welcome"])
                self.fields["show_welcome"] = welcome
                form.addRow(welcome)
                for key, label in [("active_color", "Active tab color"), ("inactive_color", "Inactive tab color")]:
                    button = QPushButton(self.values[key])
                    self.style_color_button(button, self.values[key])
                    button.clicked.connect(lambda checked=False, k=key, b=button: self.choose_color(k, b))
                    form.addRow(label, button)
                form.addRow(QLabel("Right-click a tab to assign its own color."))
            else:
                spell = QCheckBox("Enable spell checking")
                spell.setChecked(self.values["spell"])
                self.fields["spell"] = spell
                form.addRow(spell)
                language = QComboBox()
                try:
                    import enchant
                    language.addItems(sorted(enchant.list_languages()))
                except (ImportError, OSError):
                    pass
                language.setCurrentText(self.values["spell_language"])
                self.fields["spell_language"] = language
                form.addRow("Dictionary", language)
                form.addRow(QLabel("Plain text and Markdown prose; Bash comments only.\nRequires an installed Enchant dictionary."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_color(self, key, button):
        color = choose_editor_color(QColor(self.values[key]), self)
        if color.isValid():
            self.values[key] = color.name()
            button.setText(color.name())
            self.style_color_button(button, color.name())

    @staticmethod
    def style_color_button(button, value):
        foreground = "#202020" if QColor(value).lightness() > 115 else "#ffffff"
        button.setStyleSheet(f"QPushButton {{ background-color: {value}; color: {foreground}; border: 1px solid #999; border-radius: 4px; padding: 6px 12px; }}")

    def options(self):
        values = dict(self.values)
        for key, field in self.fields.items():
            if key in ("system", "editor_system"):
                continue
            if isinstance(field, QCheckBox):
                values[key] = field.isChecked()
            elif isinstance(field, QFontComboBox):
                values[key] = field.currentFont().family()
            elif isinstance(field, QDoubleSpinBox):
                values[key] = field.value()
            else:
                values[key] = field.currentText()
        if self.fields["system"].isChecked():
            values["interface_font"] = "System"
        if self.fields["editor_system"].isChecked():
            values["editor_font"] = "System Monospace"
        values["tab_width"] = int(values["tab_width"])
        return values


class AppWindow(Window):
    def __init__(self, store, identity=None, record=None):
        self.store = store
        self.identity = identity or uuid.uuid4().hex
        self.options = dict(store.settings)
        self.loading = True
        self.recovery_error = None
        super().__init__()
        self.setWindowTitle("nex-editg")
        from git_browser import GitModel
        old_model = self.model
        self.model = GitModel(self)
        self.tree.setModel(self.model)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.sidebar_menu)
        self.sidebar_title.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sidebar_title.customContextMenuRequested.connect(self.folder_title_menu)
        self.model.directoryLoaded.connect(self.restore_sidebar)
        self.tree.expanded.connect(self.schedule_recovery)
        self.tree.collapsed.connect(self.schedule_recovery)
        self.tree.selectionModel().currentChanged.connect(self.schedule_recovery)
        self.splitter.splitterMoved.connect(self.schedule_recovery)
        for column in range(2, 4):
            self.tree.hideColumn(column)
        from PyQt6.QtWidgets import QHeaderView
        self.tree.showColumn(1)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setMinimumSectionSize(24)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 28)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        old_model.deleteLater()
        self.tabs.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.tabBar().customContextMenuRequested.connect(self.tab_menu)
        self.tabs.tabBar().tabMoved.connect(self.tab_moved)
        self.spaces_control = QCheckBox("Spaces")
        self.spaces_control.setToolTip("Insert spaces instead of tab characters")
        self.spaces_control.toggled.connect(self.set_spaces)
        self.spell_control = QCheckBox("Spelling")
        self.spell_control.setChecked(self.options["spell"])
        self.spell_control.toggled.connect(self.set_spelling)
        status = self.findChild(QWidget, "status")
        status.layout().insertWidget(3, self.spaces_control)
        status.layout().insertWidget(4, self.spell_control)
        old_language = self.language
        self.language = QToolButton()
        self.language.setStyleSheet("QToolButton { border: 0; background: transparent; padding: 2px 8px; }")
        language_menu = QMenu(self.language)
        for title in ("Automatic", "Plain Text", "Bash", "Markdown"):
            language_menu.addAction(title, lambda checked=False, selected=title: self.set_language(selected))
        self.language.setMenu(language_menu)
        self.language.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        status.layout().replaceWidget(old_language, self.language)
        old_language.deleteLater()
        self.recovery_timer = QTimer(self)
        self.recovery_timer.setSingleShot(True)
        self.recovery_timer.setInterval(250)
        self.recovery_timer.timeout.connect(self.persist)
        self.action("Restore Closed Tab…", self.restore_closed, "Ctrl+Shift+T")
        self.open_menu.addSeparator()
        self.open_menu.addAction(self.actions()[-1])
        for action in self.actions():
            if action.text() == "Quit":
                action.triggered.disconnect()
                action.triggered.connect(self.close_all)
        finder = QWidget()
        finder.setLayout(self.find_bar.layout())
        find_layout = QVBoxLayout(self.find_bar)
        find_layout.setContentsMargins(8, 4, 8, 4)
        find_layout.addWidget(finder)
        replace_layout = QHBoxLayout()
        find_layout.addLayout(replace_layout)
        from PyQt6.QtWidgets import QLineEdit
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace with")
        replace_layout.addWidget(QLabel("Replace"))
        replace_layout.addWidget(self.replace_input)
        self.case_control = QCheckBox("Match case")
        replace_layout.addWidget(self.case_control)
        for label, callback in [("Replace", self.replace_one), ("Replace All", self.replace_all)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            replace_layout.addWidget(button)
        if record:
            self.apply_session(record)
        self.recent = self.store.recent() or self.recent
        self.loading = False
        self.apply_options()
        self.refresh()
        self.persist()

    def create_editor(self):
        return EnhancedEditor(self.options)

    def create_tabbar(self):
        return ColorTabs(self)

    def remember(self, path):
        try:
            previous = self.store.recent() or self.recent
            recent = [path] + [value for value in previous if value != path][:19]
            atomic_json(self.store.root / "recent.json", [str(value) for value in recent])
            for window in self.windows:
                if isinstance(window, AppWindow) and window.store is self.store:
                    window.recent = list(recent)
        except (OSError, ValueError) as error:
            self.report("Could not update recent items", error)

    def toggle_sidebar(self):
        self.sidebar.setVisible(self.sidebar.isHidden())
        self.schedule_recovery()
        self.refresh()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.schedule_recovery()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.schedule_recovery()

    def toggle_pin(self, editor, button):
        if editor.pinned and self.is_welcome(editor):
            self.set_welcome_enabled(False)
            return
        editor.pinned = not editor.pinned
        from PyQt6.QtGui import QIcon
        button.setIcon(QIcon(str(Path(__file__).parent / "icons" / ("pin-filled.svg" if editor.pinned else "pin.svg"))))
        button.setToolTip("Unpin tab" if editor.pinned else "Pin tab")
        button.setAccessibleName(button.toolTip())
        editor.close_button.setVisible(not editor.pinned)
        index = self.tabs.indexOf(editor)
        pinned_others = sum(self.tabs.widget(i).pinned for i in range(self.tabs.count()) if self.tabs.widget(i) is not editor)
        previous = self.loading
        self.loading = True
        try:
            self.tabs.tabBar().moveTab(index, pinned_others)
            self.tabs.setCurrentWidget(editor)
        finally:
            self.loading = previous
        self.schedule_recovery()
        self.refresh()

    def tab_moved(self, before, after):
        if self.loading:
            return
        editor = self.tabs.widget(after)
        pinned = sum(self.tabs.widget(i).pinned for i in range(self.tabs.count()))
        self.loading = True
        try:
            if editor.pinned:
                self.tabs.tabBar().moveTab(after, before)
            elif after < pinned:
                self.tabs.tabBar().moveTab(after, pinned)
        finally:
            self.loading = False
        self.schedule_recovery()

    def add_editor(self, editor):
        super().add_editor(editor)
        index = self.tabs.indexOf(editor)
        bar = self.tabs.tabBar()
        editor.pin_button = bar.tabButton(index, bar.ButtonPosition.LeftSide)
        editor.close_button = bar.tabButton(index, bar.ButtonPosition.RightSide)
        controls = QWidget()
        controls.setFixedSize(48, 22)
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)
        editor.pin_button.setParent(controls)
        editor.close_button.setParent(controls)
        bar.setTabButton(index, bar.ButtonPosition.LeftSide, None)
        controls_layout.addWidget(editor.pin_button)
        controls_layout.addWidget(editor.close_button)
        bar.setTabButton(index, bar.ButtonPosition.RightSide, controls)
        editor.pin_button.show()
        editor.close_button.setVisible(not editor.pinned)
        controls.show()
        editor.textChanged.connect(self.schedule_recovery)
        editor.cursorPositionChanged.connect(self.schedule_recovery)
        editor.SCN_UPDATEUI.connect(lambda *_: self.refresh())
        if not self.loading:
            editor.apply_font(self.editor_font)
            editor.configure_language()
            self.schedule_recovery()

    def refresh(self, *_):
        super().refresh()
        if hasattr(self, "spaces_control") and self.editor():
            editor = self.editor()
            self.spaces_control.blockSignals(True)
            self.spaces_control.setChecked(editor.insert_spaces)
            self.spaces_control.blockSignals(False)
            self.language.blockSignals(True)
            self.language.setText(editor.language_name)
            self.language.setToolTip("Detected: " + editor.language_name)
            self.language.blockSignals(False)
            self.tabs.tabBar().update()
            for index in range(self.tabs.count()):
                document = self.tabs.widget(index)
                if not hasattr(document, "pin_button"):
                    continue
                background = document.tab_color or self.options["active_color" if index == self.tabs.currentIndex() else "inactive_color"]
                foreground = "#333" if QColor(background).lightness() > 115 else "#fff"
                document.pin_button.setIcon(tab_icon("pin-filled" if document.pinned else "pin", foreground))
                document.close_button.setIcon(tab_icon("close", foreground))
        self.schedule_recovery()

    def schedule_recovery(self, *_):
        if not self.loading and hasattr(self, "recovery_timer"):
            self.recovery_timer.start()

    def document_record(self, editor):
        return dict(title=editor.title, path=str(editor.path) if editor.path else None,
                    text=editor.text(), modified=editor.isModified(), encoding=editor.encoding,
                    bom=base64.b64encode(editor.bom).decode(),
                    disk=base64.b64encode(editor.disk_bytes).decode() if editor.disk_bytes is not None else None,
                    cursor=list(editor.getCursorPosition()), selection=list(editor.getSelection()),
                    scroll=editor.firstVisibleLine(), horizontal=editor.SendScintilla(editor.SCI_GETXOFFSET),
                    pinned=editor.pinned, color=editor.tab_color, language=editor.language_override,
                    tab_width=editor.tabWidth(), spaces=editor.insert_spaces, eol=editor.eolMode().value,
                    ignored_words=sorted(editor.ignored_words))

    def snapshot(self):
        return dict(version=1, identity=self.identity,
                    documents=[self.document_record(self.tabs.widget(i)) for i in range(self.tabs.count())],
                    active=self.tabs.currentIndex(), workspace=str(self.workspace) if self.workspace else None,
                    sidebar=self.sidebar.isVisible(), splitter=self.splitter.sizes(),
                    recent=[str(path) for path in self.recent], tree=self.sidebar_snapshot(),
                    geometry=base64.b64encode(bytes(self.saveGeometry())).decode())

    def sidebar_snapshot(self):
        expanded = []
        def visit(parent, depth=0):
            if depth > 128:
                return
            for row in range(self.model.rowCount(parent)):
                index = self.model.index(row, 0, parent)
                if self.tree.isExpanded(index):
                    expanded.append(self.model.filePath(index))
                    visit(index, depth + 1)
        visit(self.tree.rootIndex())
        pending = getattr(self, "pending_sidebar", None) or {}
        return dict(expanded=list(dict.fromkeys(expanded + pending.get("expanded", []))),
                    selected=pending.get("selected") or self.model.filePath(self.tree.currentIndex()),
                    scroll=pending.get("scroll", self.tree.verticalScrollBar().value()))

    def restore_sidebar(self, *_):
        state = getattr(self, "pending_sidebar", None)
        if state is None:
            return
        remaining = []
        for path in state.get("expanded", []):
            index = self.model.index(path)
            if index.isValid():
                self.tree.expand(index)
            elif Path(path).exists():
                remaining.append(path)
        selected = state.get("selected")
        if selected:
            index = self.model.index(selected)
            if index.isValid():
                self.tree.setCurrentIndex(index)
                state["selected"] = None
            elif not Path(selected).exists():
                state["selected"] = None
        self.tree.verticalScrollBar().setValue(state.get("scroll", 0))
        state["expanded"] = remaining
        if not remaining and not state.get("selected"):
            scroll = state.get("scroll", 0)
            QTimer.singleShot(100, lambda: self.tree.verticalScrollBar().setValue(scroll))
            self.pending_sidebar = None

    def persist(self):
        if self.loading:
            return True
        try:
            record = self.snapshot()
            self.store.save(self.store.folder_path(self.identity, self.workspace), record)
            self.store.save(self.store.window_path(self.identity), record)
            self.recovery_error = None
            self.setWindowTitle("nex-editg")
            return True
        except (OSError, ValueError, TypeError) as error:
            self.recovery_error = str(error)
            self.setWindowTitle("nex-editg — Recovery needs attention")
            return False

    def restore_editor(self, record):
        validate_document(record)
        editor = self.create_editor()
        editor.path = Path(record["path"]) if record.get("path") else None
        editor.title = record["title"]
        editor.encoding = record.get("encoding", "utf-8")
        editor.bom = base64.b64decode(record.get("bom", ""), validate=True)
        editor.disk_bytes = base64.b64decode(record["disk"], validate=True) if record.get("disk") is not None else None
        text = record["text"]
        if editor.path and not record.get("modified"):
            try:
                editor.load(editor.path)
                text = editor.text()
            except (OSError, ValueError, UnicodeError):
                # A missing or newly unreadable file must not discard cached text.
                record = dict(record, modified=True)
        editor.setText(text)
        if record.get("modified") or not editor.path:
            editor.setEolMode(editor.EolMode(record.get("eol", editor.EolMode.EolUnix.value)))
        editor.SendScintilla(editor.SCI_EMPTYUNDOBUFFER)
        editor.setModified(bool(record.get("modified")))
        editor.tab_color = record.get("color") if QColor(record.get("color") or "").isValid() else None
        editor.language_override = record.get("language")
        editor.ignored_words = set(record.get("ignored_words", []))
        editor.setTabWidth(record.get("tab_width", self.options["tab_width"]))
        editor.insert_spaces = record.get("spaces", self.options["spaces"])
        editor.configure_language()
        self.add_editor(editor)
        if record.get("pinned"):
            index = self.tabs.indexOf(editor)
            self.toggle_pin(editor, editor.pin_button)
        selection = record.get("selection", [-1] * 4)
        if len(selection) == 4 and all(value >= 0 for value in selection):
            editor.setSelection(*selection)
        else:
            editor.setCursorPosition(*record.get("cursor", [0, 0]))
        editor.setFirstVisibleLine(record.get("scroll", 0))
        editor.SendScintilla(editor.SCI_SETXOFFSET, record.get("horizontal", 0))
        return editor

    def apply_session(self, record):
        # Build recovered editors before removing any current document.
        old = [self.tabs.widget(i) for i in range(self.tabs.count())]
        old_loading = self.loading
        self.loading = True
        try:
            for document in record["documents"]:
                self.restore_editor(document)
            for editor in old:
                self.tabs.removeTab(self.tabs.indexOf(editor))
                editor.deleteLater()
            if not self.tabs.count():
                self.new_document()
            self.tabs.setCurrentIndex(max(0, min(record.get("active", 0), self.tabs.count() - 1)))
            self.workspace = Path(record["workspace"]) if record.get("workspace") else None
            if self.workspace:
                self.tree.setRootIndex(self.model.setRootPath(str(self.workspace)))
                self.sidebar_title.setText(self.workspace.name + (" (unavailable)" if not self.workspace.is_dir() else ""))
                self.sidebar_title.setToolTip(str(self.workspace))
            else:
                self.sidebar_title.setText("Files")
                self.sidebar_title.setToolTip("")
            self.tree.setVisible(self.workspace is not None)
            self.sidebar.setVisible(record.get("sidebar", bool(self.workspace)))
            self.splitter.setSizes(record.get("splitter", [240, 820]))
            self.recent = self.store.recent() or [Path(path) for path in record.get("recent", [])]
            self.pending_sidebar = dict(record.get("tree", {}))
            self.restore_sidebar()
            if record.get("geometry"):
                self.restoreGeometry(base64.b64decode(record["geometry"]))
        finally:
            self.loading = old_loading

    def set_folder(self, path):
        path = Path(path).resolve()
        if path == self.workspace:
            self.sidebar.show()
            return
        if not self.persist():
            self.report("Could not preserve current documents", self.recovery_error)
            return
        try:
            record = self.store.load(self.store.folder_path(self.identity, path))
            if record is None:
                record = dict(version=1, documents=[], active=0, workspace=str(path), sidebar=True)
            self.apply_session(record)
            self.apply_options()
            self.remember(path)
            self.sidebar.show()
            self.persist()
        except (OSError, ValueError) as error:
            self.report("Could not open workspace", error)

    def make_folder_title_menu(self):
        if self.workspace is None:
            return None
        menu = QMenu(self)
        action = menu.addAction("Close Folder")
        action.triggered.connect(self.close_folder)
        return menu

    def folder_title_menu(self, point):
        menu = self.make_folder_title_menu()
        if menu is not None:
            menu.exec(self.sidebar_title.mapToGlobal(point))
            menu.deleteLater()

    def close_folder(self):
        if self.workspace is None:
            return
        if not self.persist():
            self.report("Could not preserve workspace", self.recovery_error)
            return
        try:
            record = self.store.load(self.store.folder_path(self.identity, None))
            self.apply_session(record or dict(version=1, documents=[], active=0, sidebar=True))
            self.sidebar.show()
            self.apply_options()
            self.persist()
        except (OSError, ValueError) as error:
            self.report("Could not close workspace", error)

    def confirm_close(self, editor, *, closing_tab=False):
        if not self.persist():
            self.report("Recovery could not be written; document kept open", self.recovery_error)
            return False
        if not editor.isModified():
            return True
        if closing_tab:
            answer = QMessageBox.warning(
                self, "Unsaved changes", f"Save changes to {editor.title}?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if answer == QMessageBox.StandardButton.Save:
                return self.save_editor(editor)
            return answer == QMessageBox.StandardButton.Discard
        if not self.options["prompt_on_close"]:
            return True
        prompt = QMessageBox(self)
        prompt.setWindowTitle("Unsaved changes")
        prompt.setText(f"Save {editor.title}, or keep its recovery copy?")
        save = prompt.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        keep = prompt.addButton("Keep Recovery", QMessageBox.ButtonRole.ActionRole)
        cancel = prompt.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        prompt.setDefaultButton(cancel)
        prompt.exec()
        if prompt.clickedButton() not in (save, keep):
            return False
        return self.save_editor(editor) if prompt.clickedButton() == save else True

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        if editor is not None and self.is_welcome(editor):
            self.set_welcome_enabled(False)
            return
        if editor is None or not self.confirm_close(editor, closing_tab=True):
            return
        try:
            self.store.archive(self.document_record(editor))
        except (OSError, ValueError) as error:
            self.report("Could not keep closed-tab recovery; document kept open", error)
            return
        self.tabs.removeTab(index)
        if not self.tabs.count():
            self.new_document()
        if not self.persist():
            self.add_editor(editor)
            self.report("Could not update recovery; document kept open", self.recovery_error)
            return
        editor.deleteLater()

    def closeEvent(self, event):
        for index in range(self.tabs.count()):
            if not self.confirm_close(self.tabs.widget(index)):
                event.ignore()
                return
        if not self.persist():
            self.report("Could not preserve window; kept open", self.recovery_error)
            event.ignore()
            return
        self.recovery_timer.stop()
        self.model.timer.stop()
        self.windows.remove(self)
        event.accept()

    def new_window(self):
        child = type(self)(self.store)
        child.show()

    def close_all(self):
        for window in list(self.windows):
            if isinstance(window, AppWindow) and window.store is self.store and not window.close():
                break

    def restore_closed(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore Closed Tab", str(self.store.root / "closed-tabs"), "Recovery (*.json)")
        if path:
            try:
                self.restore_editor(json.loads(Path(path).read_text()))
                self.persist()
            except (OSError, ValueError) as error:
                self.report("Could not restore closed tab", error)

    def save_editor(self, editor, as_new=False):
        original_encoding, original_bom = editor.encoding, editor.bom
        if as_new:
            editor.encoding, editor.bom = "utf-8", b""
        result = super().save_editor(editor, as_new)
        if result:
            editor.configure_language()
            self.persist()
        elif as_new:
            editor.encoding, editor.bom = original_encoding, original_bom
        return result

    def set_language(self, selected):
        self.editor().configure_language(selected)
        self.schedule_recovery()

    def find_next(self):
        if self.editor() and self.find_input.text():
            self.editor().findFirst(self.find_input.text(), False, self.case_control.isChecked(), False, True)

    def replace_one(self):
        editor = self.editor()
        query = self.find_input.text()
        if not query:
            return
        selected = editor.selectedText()
        matches = selected == query if self.case_control.isChecked() else selected.casefold() == query.casefold()
        if not matches:
            self.find_next()
            selected = editor.selectedText()
            matches = selected == query if self.case_control.isChecked() else selected.casefold() == query.casefold()
        if matches:
            editor.replaceSelectedText(self.replace_input.text())
            self.find_next()

    def replace_all(self):
        query = self.find_input.text()
        if not query:
            return
        editor = self.editor()
        result, count = re.subn(re.escape(query), lambda _: self.replace_input.text(), editor.text(), flags=0 if self.case_control.isChecked() else re.IGNORECASE)
        if count:
            data = result.encode("utf-8")
            editor.beginUndoAction()
            try:
                editor.SendScintilla(editor.SCI_SETTARGETSTART, 0)
                editor.SendScintilla(editor.SCI_SETTARGETEND, editor.length())
                editor.SendScintilla(editor.SCI_REPLACETARGET, len(data), data)
            finally:
                editor.endUndoAction()

    def set_spaces(self, enabled):
        self.editor().insert_spaces = enabled
        self.schedule_recovery()

    def change_tab_width(self, index):
        super().change_tab_width(index)
        self.schedule_recovery()

    def set_spelling(self, enabled):
        values = dict(self.options, spell=enabled)
        try:
            self.store.save_settings(values)
        except (OSError, ValueError) as error:
            self.report("Could not save spelling preference", error)
            return
        for window in list(self.windows):
            if isinstance(window, AppWindow) and window.store is self.store:
                window.options.update(values)
                window.spell_control.blockSignals(True)
                window.spell_control.setChecked(enabled)
                window.spell_control.blockSignals(False)
                for index in range(window.tabs.count()):
                    editor = window.tabs.widget(index)
                    editor.options = window.options
                    editor.check_spelling()
        if enabled and not self.editor().spelling_available:
            self.report("Spell checking is unavailable", self.editor().spelling_error)

    def tab_menu(self, point):
        index = self.tabs.tabBar().tabAt(point)
        if index < 0:
            return
        menu = QMenu(self)
        document = self.tabs.widget(index)
        menu.addAction("Rename…", lambda: self.rename_tab(document))
        menu.addSeparator()
        menu.addAction("Tab Color…", lambda: self.choose_tab_color(index))
        menu.addAction("Use Default Color", lambda: self.reset_tab_color(index))
        menu.exec(self.tabs.tabBar().mapToGlobal(point))

    def sidebar_menu(self, point):
        index = self.tree.indexAt(point)
        if not index.isValid() or self.model.isDir(index):
            return
        path = Path(self.model.filePath(index))
        self.tree.setCurrentIndex(index.siblingAtColumn(0))
        menu = QMenu(self)
        menu.addAction("Rename…", lambda: self.rename_sidebar_file(path))
        menu.addAction("Delete…", lambda: self.delete_sidebar_file(path))
        menu.exec(self.tree.viewport().mapToGlobal(point))

    def rename_sidebar_file(self, path, name=None):
        if name is None:
            name, accepted = QInputDialog.getText(self, "Rename File", "File name:", text=path.name)
            if not accepted:
                return False
        # A closed file can be renamed without opening or decoding its contents.
        from types import SimpleNamespace
        return self.rename_document(SimpleNamespace(path=path), name)

    def delete_sidebar_file(self, path, confirm=None, trash=None):
        if path.is_dir():
            return False
        if confirm is None:
            answer = QMessageBox.question(self, "Delete File?", f"Are you sure you want to move ‘{path.name}’ to Trash?\n\nOpen copies will be kept as unsaved documents.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            confirm = answer == QMessageBox.StandardButton.Yes
        if not confirm:
            return False
        moved = False
        try:
            peers = [window for window in self.windows if isinstance(window, AppWindow) and window.store is self.store]
            for window in peers:
                if not window.persist():
                    raise OSError("Could not preserve recovery before deleting.")
                for index in range(window.tabs.count()):
                    document = window.tabs.widget(index)
                    if document.path == path:
                        self.store.archive(window.document_record(document))
            success, _ = (trash or QFile.moveToTrash)(str(path))
            if not success:
                raise OSError("Could not move the file to Trash. The file has been kept.")
            moved = True
            for window in peers:
                for index in range(window.tabs.count()):
                    document = window.tabs.widget(index)
                    if document.path == path:
                        document.path = None
                        document.disk_bytes = None
                        document.setModified(True)
                window.refresh()
                window.model.scan()
            for window in peers:
                if not window.persist():
                    raise OSError("File moved to Trash, but recovery needs attention. Keep this window open.")
            self.detach_deleted_recovery(path)
            recent = [value for value in self.store.recent() if value != path]
            atomic_json(self.store.root / "recent.json", [str(value) for value in recent])
            for window in peers:
                window.recent = recent
            return True
        except (OSError, ValueError) as error:
            self.report("File deleted; recovery needs attention" if moved else "Could not delete file", error)
            return False

    def detach_deleted_recovery(self, deleted):
        for path in self.store.root.rglob("*.json"):
            if ".corrupt-" in path.name:
                continue
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            documents = record.get("documents", [record]) if isinstance(record, dict) else []
            changed = False
            for document in documents:
                if isinstance(document, dict) and document.get("path") == str(deleted):
                    document.update(path=None, modified=True, disk=None)
                    changed = True
            if changed:
                atomic_json(path, record)

    def rename_tab(self, editor):
        if editor.path is None and self.workspace is None:
            # No sidebar folder: the ordinary Save As dialog chooses a location.
            self.save_editor(editor, as_new=True)
            return
        name, accepted = QInputDialog.getText(self, "Rename File", "File name:", text=editor.path.name if editor.path else "")
        if accepted:
            self.rename_document(editor, name)

    def rename_document(self, editor, name):
        old = editor.path
        committed = False
        try:
            if not name or name in (".", "..") or any(character in name for character in ("/", "\\", "\0")):
                raise ValueError("Enter a file name without folder separators.")
            directory = old.parent if old else self.workspace
            if directory is None:
                raise ValueError("Open a workspace folder or use Save As to choose a location.")
            target = directory / name
            if old == target:
                return True
            if os.path.lexists(target):
                raise FileExistsError("A file or folder with that name already exists.")
            peers = [window for window in self.windows if isinstance(window, AppWindow) and window.store is self.store]
            for window in peers:
                if any(window.tabs.widget(i).path == target for i in range(window.tabs.count())):
                    raise ValueError("That file is already open in another tab.")
                if not window.persist():
                    raise OSError("Could not preserve recovery before renaming.")
            if old:
                # Exclusive link creation refuses overwrites, including races.
                os.link(old, target, follow_symlinks=False)
                try:
                    old.unlink()
                except OSError:
                    target.unlink()
                    raise
            else:
                data = editor.text().encode("utf-8")
                descriptor, temporary = tempfile.mkstemp(prefix=".gedit-new-", dir=directory)
                try:
                    with os.fdopen(descriptor, "wb") as output:
                        output.write(data); output.flush(); os.fsync(output.fileno())
                    os.link(temporary, target)
                finally:
                    os.unlink(temporary)
                editor.encoding, editor.bom, editor.disk_bytes = "utf-8", b"", data
                editor.setModified(False)
            committed = True
            for window in peers:
                for i in range(window.tabs.count()):
                    document = window.tabs.widget(i)
                    if document is editor or (old is not None and document.path == old):
                        document.path, document.title = target, target.name
                        document.configure_language()
                window.refresh()
                window.model.scan()
            for window in peers:
                if not window.persist():
                    raise OSError("The file was renamed, but recovery could not be updated. Keep the document open.")
            if old:
                self.update_renamed_recovery(old, target)
                recent = [value for value in self.store.recent() if value != old]
                atomic_json(self.store.root / "recent.json", [str(value) for value in recent])
            self.remember(target)
            return True
        except (OSError, ValueError, UnicodeError) as error:
            self.report("File renamed; recovery needs attention" if committed else "Could not rename file", error)
            return False

    def update_renamed_recovery(self, old, target):
        # Update inactive folder snapshots and closed-tab references as well.
        for path in self.store.root.rglob("*.json"):
            if ".corrupt-" in path.name:
                continue
            try:
                record = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            documents = record.get("documents", [record]) if isinstance(record, dict) else []
            changed = False
            for document in documents:
                if isinstance(document, dict) and document.get("path") == str(old):
                    document.update(path=str(target), title=target.name)
                    changed = True
            if isinstance(record, dict) and isinstance(record.get("sidebar"), dict) and record["sidebar"].get("selected") == str(old):
                record["sidebar"]["selected"] = str(target)
                changed = True
            if changed:
                atomic_json(path, record)

    def choose_tab_color(self, index):
        editor = self.tabs.widget(index)
        color = choose_editor_color(QColor(editor.tab_color or self.options["active_color"]), self)
        if color.isValid():
            editor.tab_color = color.name()
            self.refresh()
            self.persist()

    def reset_tab_color(self, index):
        self.tabs.widget(index).tab_color = None
        self.refresh()
        self.persist()

    def apply_options(self):
        interface = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont) if self.options["interface_font"] == "System" else QFont(self.options["interface_font"])
        interface.setPointSizeF(self.options["interface_px"] * 72 / 96)
        self.setFont(interface)
        sidebar = QFont(interface)
        sidebar.setPointSizeF(self.options["sidebar_px"] * 72 / 96)
        self.sidebar.setFont(sidebar)
        tab = QFont(interface)
        tab.setPointSizeF(self.options["tab_px"] * 72 / 96)
        self.tabs.tabBar().setFont(tab)
        self.editor_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont) if self.options["editor_font"] == "System Monospace" else QFont(self.options["editor_font"])
        self.editor_font.setPointSizeF(self.options["editor_pt"])
        self.model.set_enabled(self.options["show_git"])
        self.spell_control.blockSignals(True)
        self.spell_control.setChecked(self.options["spell"])
        self.spell_control.blockSignals(False)
        for index in range(self.tabs.count()):
            editor = self.tabs.widget(index)
            editor.options = self.options
            if editor.dictionary is None or editor.dictionary.tag != self.options["spell_language"]:
                try:
                    import enchant
                    editor.dictionary = enchant.Dict(self.options["spell_language"])
                    editor.spelling_available = True
                except Exception as error:
                    editor.dictionary = None
                    editor.spelling_available = False
                    editor.spelling_error = str(error)
            editor.apply_font(self.editor_font)
            editor.configure_language()
        self.refresh()

    def preferences(self):
        dialog = Preferences(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.options()
            try:
                self.store.save_settings(values)
            except (OSError, ValueError) as error:
                self.report("Could not save preferences", error)
                return
            for window in list(self.windows):
                if isinstance(window, AppWindow) and window.store is self.store:
                    window.options = dict(values)
                    window.apply_options()
                    if not values["show_welcome"]:
                        window.dismiss_welcome()
            if values["show_welcome"]:
                self.show_welcome()
            self.spell_control.blockSignals(True)
            self.spell_control.setChecked(values["spell"])
            self.spell_control.blockSignals(False)

    def is_welcome(self, editor):
        return editor.path == self.store.root / "Welcome.sh"

    def dismiss_welcome(self):
        for index in reversed(range(self.tabs.count())):
            editor = self.tabs.widget(index)
            if self.is_welcome(editor):
                try:
                    self.store.archive(self.document_record(editor))
                except (OSError, ValueError) as error:
                    self.report("Could not preserve Welcome edits", error)
                    return
                self.tabs.removeTab(index)
                if not self.tabs.count():
                    self.new_document()
                if not self.persist():
                    self.add_editor(editor)
                    return
                editor.deleteLater()

    def set_welcome_enabled(self, enabled):
        values = dict(self.store.settings, show_welcome=enabled)
        try:
            self.store.save_settings(values)
        except (OSError, ValueError) as error:
            self.report("Could not save Welcome preference", error)
            return
        for window in list(self.windows):
            if isinstance(window, AppWindow) and window.store is self.store:
                window.options = dict(values)
                if not enabled:
                    window.dismiss_welcome()

    def show_welcome(self):
        target = self.store.root / "Welcome.sh"
        supplied = (Path(__file__).parent / "Examples" / "Welcome.sh").read_text()
        previous = supplied.replace("# A familiar place to write, designed to be pleasant to use.\n", "", 1)
        if not target.exists() or target.read_text() == previous:
            target.write_text(supplied)
        self.open_path(target)
        if not self.editor().isModified() and self.editor().text() == previous:
            self.editor().load(target)
        editor = self.editor()
        if not editor.pinned:
            self.toggle_pin(editor, editor.pin_button)

    def help(self):
        QMessageBox.information(self, "nex-editg Editing", "Alt-drag selects columns. Ctrl+Shift+T restores a closed-tab recovery copy.\n\nBottom controls select language, tab width, spaces and spelling. Right-click a tab for its color.\n\nUnsaved text is kept in independent recovery storage. Closing never writes edits to original files unless you choose Save.")

    def about(self):
        QMessageBox.information(self, "About nex-editg", "nex-editg\nQt 6 Widgets + QScintilla\nIndependent settings, workspace sessions and recovery.\n" + str(self.store.root))


def launch(app, transient=False, root_override=None, paths=()):
    if root_override:
        root = Path(root_override).expanduser().resolve()
    elif transient:
        root = Path(tempfile.mkdtemp(prefix="gedit-preview-"))
    else:
        root = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    try:
        store = Store(root)
        lock = QLockFile(str(root / "instance.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            from PyQt6.QtNetwork import QLocalSocket
            socket = QLocalSocket()
            socket.connectToServer(str(root / "editor.sock"))
            if socket.waitForConnected(1000):
                socket.write(json.dumps(dict(paths=[str(Path(path).expanduser().resolve()) for path in paths])).encode() + b"\n")
                socket.flush()
                socket.waitForBytesWritten(1000)
                socket.disconnectFromServer()
                return [], None
            QMessageBox.information(None, "nex-editg is already running", "Use the existing nex-editg window. New Window opens another window with separate recovery.")
            return [], None
        records = []
        if not transient:
            for path in sorted((root / "windows").glob("*.json")):
                if ".previous." not in path.name and ".corrupt-" not in path.name:
                    record = store.load(path)
                    if record:
                        records.append(record)
        windows = [AppWindow(store, record.get("identity"), record) for record in records] or [AppWindow(store)]
        if not transient:
            if store.settings["show_welcome"]:
                windows[0].show_welcome()
            else:
                for window in windows:
                    window.dismiss_welcome()
        for window in windows:
            window.show()
        from PyQt6.QtNetwork import QLocalServer
        server = QLocalServer(app)
        socket_path = str(root / "editor.sock")
        QLocalServer.removeServer(socket_path)
        if server.listen(socket_path):
            def connection():
                socket = server.nextPendingConnection()
                buffer = bytearray()
                def receive():
                    buffer.extend(bytes(socket.readAll()))
                    if len(buffer) > 262144:
                        socket.abort()
                        return
                    if b"\n" not in buffer:
                        return
                    try:
                        request = json.loads(bytes(buffer).split(b"\n", 1)[0])
                        requested = request.get("paths", [])
                        if not isinstance(requested, list) or any(not isinstance(path, str) for path in requested):
                            return
                        active = app.activeWindow()
                        targets = [window for window in AppWindow.windows if window.store is store]
                        if not targets:
                            return
                        target = active if isinstance(active, AppWindow) and active.store is store else targets[0]
                        for path in requested:
                            target.open_path(Path(path))
                        if target.isMinimized():
                            target.showNormal()
                        target.raise_()
                        target.activateWindow()
                        target.editor().setFocus()
                    except (ValueError, TypeError):
                        pass
                    finally:
                        socket.disconnectFromServer()
                socket.readyRead.connect(receive)
                socket.disconnected.connect(socket.deleteLater)
                receive()
            server.newConnection.connect(connection)
            app._instance_server = server
        return windows, lock
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, "Could not start safely", str(error) + "\nExisting recovery data has been preserved.")
        return [], None
