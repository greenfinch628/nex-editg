"""Core Qt 6 / QScintilla widgets; the enhanced application is in enhancements.py."""
from __future__ import annotations

import argparse
import codecs
from pathlib import Path
import sys

from PyQt6.QtCore import QDir, QPoint, QSize, Qt, QSaveFile, QIODevice, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence, QFileSystemModel, QMouseEvent
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QFontDialog, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QSplitter,
    QTabBar, QTabWidget, QToolButton, QTreeView, QVBoxLayout, QWidget,
)
from PyQt6.Qsci import QsciScintilla


APP_VERSION = Path(__file__).resolve().with_name("VERSION").read_text().strip()


STYLE = """
QMainWindow, QWidget#root { background: #e0e0e0; color: #202020; }
QWidget#header { background: #d8d8d8; border-bottom: 1px solid #bcbcbc; }
QToolButton { border: 1px solid #aaa; border-radius: 5px; background: #eeeeee;
              padding: 6px 10px; color: #202020; }
QToolButton:hover { background: #fafafa; }
QToolButton:pressed { background: #c8c8c8; }
QTabWidget::pane { border: 0; background: white; }
QTabBar { background: #e0e0e0; }
QTabBar::tab { background: #f8f8f8; color: #202020; border: 1px solid #bcbcbc;
              border-bottom: 3px solid transparent; border-top-left-radius: 7px;
              border-top-right-radius: 7px; padding: 8px 12px; margin: 4px 1px 0px; }
QTabBar::tab:selected { background: #e8e8e8; border-bottom: 3px solid #3584e4; }
QTabBar QToolButton { padding: 0; border: 0; background: transparent; }
QToolButton#appButton::menu-indicator { image: none; width: 0; }
QWidget#sidebar { background: #f8f8f8; }
QTreeView { background: #f8f8f8; color: #202020; border: 0; }
QTreeView::item { padding: 3px; }
QTreeView::item:selected { background: #d7e7fa; color: #202020; }
QWidget#status { background: #e0e0e0; border-top: 1px solid #c6c6c6; }
QMenu { background: #fafafa; color: #202020; border: 1px solid #aaa; padding: 4px; }
QMenu::item { padding: 6px 24px; }
QMenu::item:selected { background: #d7e7fa; }
"""


class Editor(QsciScintilla):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.path: Path | None = None
        self.disk_bytes: bytes | None = None
        self.encoding = "utf-8"
        self.bom = b""
        self.title = "Untitled Document"
        self.pinned = False
        # QScintilla consumes pointSize(); a pixel-sized QFont yields -1 there.
        font = QFont("DejaVu Sans Mono", 12)
        self.setFont(font)
        self.setMarginsFont(font)
        self.setUtf8(True)
        self.setColor(QColor("#000000"))
        self.setPaper(QColor("#ffffff"))
        self.setMarginsBackgroundColor(QColor("#e0e0e0"))
        self.setMarginsForegroundColor(QColor("#555555"))
        self.setMarginType(0, self.MarginType.NumberMargin)
        self.setMarginLineNumbers(0, True)
        self.setMarginWidth(0, 54)
        self.setMarginWidth(1, 3)
        self.SendScintilla(self.SCI_SETMARGINTYPEN, 1, self.SC_MARGIN_BACK)
        self.SendScintilla(self.SCI_SETMARGINBACKN, 1, QColor("#ffffff"))
        self.setMarginWidth(2, 0)
        self.setTabWidth(2)
        self.setIndentationsUseTabs(False)
        self.setAutoIndent(False)
        self.setWrapMode(self.WrapMode.WrapNone)
        self.setEolMode(self.EolMode.EolUnix)
        self.setSelectionBackgroundColor(QColor("#c9def7"))
        self.setSelectionForegroundColor(QColor("#000000"))
        self.setCaretForegroundColor(QColor("#000000"))
        self.SendScintilla(self.SCI_SETADDITIONALSELECTIONTYPING, 1)
        self.SendScintilla(self.SCI_SETMULTIPLESELECTION, 1)
        self.SendScintilla(self.SCI_SETVIRTUALSPACEOPTIONS, self.SCVS_RECTANGULARSELECTION)
        self.SendScintilla(self.SCI_SETMULTIPASTE, self.SC_MULTIPASTE_EACH)
        self.SendScintilla(self.SCI_SETADDITIONALCARETFORE, QColor("#3584e4"))
        self.SendScintilla(self.SCI_SETMARGINLEFT, 10)

    def mousePressEvent(self, event):
        # QScintilla's Linux backend hardcodes Ctrl for the initial block click;
        # subsequent motion already uses Alt. Map only the initial Alt press.
        if sys.platform.startswith("linux") and event.button() == Qt.MouseButton.LeftButton and event.modifiers() & Qt.KeyboardModifier.AltModifier:
            mapped = QMouseEvent(event.type(), event.position(), event.globalPosition(), event.button(), event.buttons(), event.modifiers() | Qt.KeyboardModifier.ControlModifier)
            super().mousePressEvent(mapped)
            event.setAccepted(mapped.isAccepted())
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Tab and event.modifiers() == Qt.KeyboardModifier.NoModifier and not self.SendScintilla(self.SCI_SELECTIONISRECTANGLE):
            # Keep literal Tab insertion, while virtual-space padding uses spaces.
            self.replaceSelectedText("\t")
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            pos = self.SendScintilla(self.SCI_GETCURRENTPOS)
            self.SendScintilla(self.SCI_SETEMPTYSELECTION, pos)
            event.accept()
            return
        super().keyPressEvent(event)

    def paste(self, text=None):
        count = self.SendScintilla(self.SCI_GETSELECTIONS)
        if count < 2 and not self.SendScintilla(self.SCI_SELECTIONISRECTANGLE):
            super().paste()
            return
        if self.isReadOnly():
            return
        text = (QApplication.clipboard().text() if text is None else text).replace("\r\n", "\n").replace("\r", "\n")
        if not text:
            return
        rows = text.split("\n")
        if len(rows) == count + 1 and rows[-1] == "":
            rows.pop()  # QScintilla's rectangular clipboard includes a final newline.
        if len(rows) not in (1, count):
            QMessageBox.information(self, "Column paste", "Paste one line or one line per selected row.")
            return
        selections = []
        for index in range(count):
            start = self.SendScintilla(self.SCI_GETSELECTIONNSTART, index)
            end = self.SendScintilla(self.SCI_GETSELECTIONNEND, index)
            padding = min(self.SendScintilla(self.SCI_GETSELECTIONNANCHORVIRTUALSPACE, index), self.SendScintilla(self.SCI_GETSELECTIONNCARETVIRTUALSPACE, index))
            selections.append((start, end, padding))
        selections.sort()
        replacements = []
        for index, (start, end, padding) in enumerate(selections):
            row = rows[0] if len(rows) == 1 else rows[index]
            replacements.append((start, end, ((" " * padding if row else "") + row).encode("utf-8")))
        self.beginUndoAction()
        try:
            for start, end, value in reversed(replacements):
                self.SendScintilla(self.SCI_SETTARGETSTART, start)
                self.SendScintilla(self.SCI_SETTARGETEND, end)
                self.SendScintilla(self.SCI_REPLACETARGET, len(value), value)
        finally:
            self.endUndoAction()
        delta = 0
        positions = []
        for start, end, value in replacements:
            positions.append(start + delta + len(value))
            delta += len(value) - (end - start)
        self.SendScintilla(self.SCI_SETEMPTYSELECTION, positions[0])
        for position in positions[1:]:
            self.SendScintilla(self.SCI_ADDSELECTION, position, position)
        self.SendScintilla(self.SCI_SETMAINSELECTION, 0)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        for title, callback, enabled in [
            ("Undo", self.undo, self.isUndoAvailable()),
            ("Redo", self.redo, self.isRedoAvailable()),
            ("Cut", self.cut, self.hasSelectedText() and not self.isReadOnly()),
            ("Copy", self.copy, self.hasSelectedText()),
            ("Paste", self.paste, bool(QApplication.clipboard().text()) and not self.isReadOnly()),
            ("Select All", self.selectAll, True),
        ]:
            action = menu.addAction(title)
            action.setEnabled(enabled)
            action.triggered.connect(lambda checked=False, call=callback: call())
        menu.exec(event.globalPos())
        menu.deleteLater()

    def load(self, path: Path):
        raw = path.read_bytes()
        for bom, encoding in [(codecs.BOM_UTF32_LE, "utf-32-le"),
                              (codecs.BOM_UTF32_BE, "utf-32-be"),
                              (codecs.BOM_UTF8, "utf-8"),
                              (codecs.BOM_UTF16_LE, "utf-16-le"),
                              (codecs.BOM_UTF16_BE, "utf-16-be")]:
            if raw.startswith(bom):
                self.bom, self.encoding = bom, encoding
                break
        payload = raw[len(self.bom):]
        if self.bom:
            text = payload.decode(self.encoding)
        else:
            if len(raw) >= 4 and len(raw) % 2 == 0 and raw[1::2].count(0) > len(raw) / 5:
                self.encoding = "utf-16-le"
            elif len(raw) >= 4 and len(raw) % 2 == 0 and raw[::2].count(0) > len(raw) / 5:
                self.encoding = "utf-16-be"
            try:
                text = payload.decode(self.encoding)
            except UnicodeDecodeError:
                try:
                    self.encoding = "cp1252"
                    text = payload.decode(self.encoding)
                except UnicodeDecodeError:
                    self.encoding = "mac_roman"
                    text = payload.decode(self.encoding)
        if "\0" in text:
            raise ValueError("This file contains binary data.")
        if any(ord(character) < 32 and character not in "\t\n\r\f" for character in text):
            raise ValueError("This file contains non-text control characters.")
        if "\r\n" in text:
            self.setEolMode(self.EolMode.EolWindows)
        elif "\r" in text:
            self.setEolMode(self.EolMode.EolMac)
        self.setText(text)
        self.SendScintilla(self.SCI_EMPTYUNDOBUFFER)
        self.setModified(False)
        self.path, self.disk_bytes, self.title = path, raw, path.name

    def encoded(self):
        return self.bom + self.text().encode(self.encoding)


class Tabs(QTabBar):
    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        return QSize(max(220, min(360, size.width())), max(40, size.height()))


class Window(QMainWindow):
    windows: list[Window] = []

    def __init__(self):
        super().__init__()
        self.windows.append(self)
        self.setWindowTitle("nex-editg")
        self.resize(1060, 720)
        self.setMinimumSize(640, 400)
        self.workspace: Path | None = None
        self.recent: list[Path] = []
        self.untitled_count = 0
        root = QWidget(objectName="root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(root)

        header = QWidget(objectName="header")
        header.setFixedHeight(62)
        row = QHBoxLayout(header)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(8)
        self.open_menu = QMenu(self)
        self.open_action = self.action("Open…", self.open_files, QKeySequence.StandardKey.Open)
        self.open_menu.addAction(self.open_action)
        self.recent_menu = self.open_menu.addMenu("Open Recent")
        self.recent_menu.aboutToShow.connect(self.fill_recent)
        self.workspace_action = self.action("Workspace…", self.choose_folder)
        self.open_menu.addAction(self.workspace_action)
        self.new_action = self.action("New File", self.new_document, QKeySequence.StandardKey.New)
        self.new_window_action = self.action("New Window", self.new_window, "Ctrl+Shift+N")
        self.close_action = self.action("Close File", self.close_current, QKeySequence.StandardKey.Close)
        self.close_folder_action = self.action("Close Folder", self.close_folder)
        for action in [self.new_action, self.new_window_action, self.close_action, self.close_folder_action]:
            self.open_menu.addAction(action)
        self.open_menu.aboutToShow.connect(lambda: self.close_folder_action.setEnabled(self.workspace is not None))
        self.open_button = self.button("Open", "document-open", "Open files or a folder")
        self.open_button.setMenu(self.open_menu)
        self.open_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.open_button.clicked.connect(lambda: self.open_menu.popup(self.open_button.mapToGlobal(QPoint(0, self.open_button.height()))))
        row.addWidget(self.open_button)
        side = self.button("▥", "view-sidetree", "Show/Hide Sidebar (F9)")
        side.clicked.connect(self.toggle_sidebar)
        row.addWidget(side)
        new = self.button("+", "document-new", "New Tab")
        new.clicked.connect(self.new_document)
        row.addWidget(new)
        row.addStretch()
        self.save_action = self.action("Save", self.save_current, QKeySequence.StandardKey.Save)
        self.save_as_action = self.action("Save As…", self.save_as, QKeySequence.StandardKey.SaveAs)
        self.save_all_action = self.action("Save All", self.save_all)
        self.save_menu = QMenu(self)
        for action in [self.save_action, self.save_as_action, self.save_all_action]:
            self.save_menu.addAction(action)
        self.save_button = self.button("Save", "document-save", "Save")
        self.save_button.setMenu(self.save_menu)
        self.save_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        self.save_button.clicked.connect(self.save_current)
        row.addWidget(self.save_button)
        app = self.button("☰", "open-menu-symbolic", "Application menu")
        app.setObjectName("appButton")
        app_menu = QMenu(self)
        app_menu.addAction(self.action("Preferences…", self.preferences, "Ctrl+,"))
        app_menu.addAction(self.action("Help", self.help))
        app_menu.addAction(self.action("About nex-editg", self.about))
        app.setMenu(app_menu)
        app.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        row.addWidget(app)
        layout.addWidget(header)

        self.splitter = QSplitter()
        self.sidebar = QWidget(objectName="sidebar")
        self.sidebar.setMinimumWidth(160)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(8, 8, 8, 0)
        side_head = QHBoxLayout()
        self.sidebar_title = QLabel("Files")
        side_head.addWidget(self.sidebar_title, 1)
        hide = QPushButton("×")
        hide.setFixedSize(28, 28)
        hide.setToolTip("Hide sidebar")
        hide.clicked.connect(self.toggle_sidebar)
        side_head.addWidget(hide)
        side_layout.addLayout(side_head)
        self.model = QFileSystemModel(self)
        self.model.setReadOnly(True)
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot)
        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        for column in range(1, 4):
            self.tree.hideColumn(column)
        self.tree.doubleClicked.connect(self.open_tree)
        side_layout.addWidget(self.tree)
        self.splitter.addWidget(self.sidebar)
        self.tabs = QTabWidget()
        self.tabs.setTabBar(self.create_tabbar())
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.refresh)
        self.splitter.addWidget(self.tabs)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([240, 820])
        self.sidebar.hide()
        layout.addWidget(self.splitter, 1)

        self.find_bar = QWidget()
        find_row = QHBoxLayout(self.find_bar)
        find_row.addWidget(QLabel("Find"))
        self.find_input = QLineEdit()
        self.find_input.returnPressed.connect(self.find_next)
        find_row.addWidget(self.find_input)
        find_next = QPushButton("Next")
        find_next.clicked.connect(self.find_next)
        find_row.addWidget(find_next)
        find_close = QPushButton("×")
        find_close.clicked.connect(self.find_bar.hide)
        find_row.addWidget(find_close)
        self.find_bar.hide()
        layout.addWidget(self.find_bar)

        status = QWidget(objectName="status")
        status.setFixedHeight(38)
        status_row = QHBoxLayout(status)
        status_row.setContentsMargins(10, 0, 18, 0)
        status_row.setSpacing(28)
        status_row.addStretch()
        self.language = QLabel("Plain Text")
        self.tab_width = QComboBox()
        self.tab_width.addItems(["Tab Width: 2", "Tab Width: 4", "Tab Width: 8"])
        self.tab_width.currentIndexChanged.connect(self.change_tab_width)
        self.position = QLabel("Ln 1, Col 1")
        self.mode = QLabel("INS")
        for item in [self.language, self.tab_width, self.position, self.mode]:
            status_row.addWidget(item)
        layout.addWidget(status)
        self.action("Show/Hide Sidebar", self.toggle_sidebar, "F9")
        self.action("Find", self.show_find, QKeySequence.StandardKey.Find)
        self.action("Find Next", self.find_next, QKeySequence.StandardKey.FindNext)
        self.action("Quit", self.close, QKeySequence.StandardKey.Quit)
        self.new_document()

    def action(self, title, callback, shortcut=None):
        action = QAction(title, self)
        action.triggered.connect(lambda checked=False: callback())
        if shortcut is not None:
            if isinstance(shortcut, QKeySequence.StandardKey):
                bindings = QKeySequence.keyBindings(shortcut)
                if shortcut == QKeySequence.StandardKey.Close:
                    preferred = QKeySequence("Ctrl+W")
                    bindings = [preferred] + [key for key in bindings if key != preferred]
                action.setShortcuts(bindings)
            else:
                action.setShortcut(QKeySequence(shortcut))
        self.addAction(action)
        return action

    @staticmethod
    def button(text, icon_name, tip):
        button = QToolButton()
        button.setText(text)
        icon = QIcon(str(Path(__file__).parent / "icons" / f"{icon_name}.svg"))
        if not icon.isNull():
            button.setIcon(icon)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon if text in ("Open", "Save") else Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def editor(self) -> Editor | None:
        return self.tabs.currentWidget()

    def add_editor(self, editor):
        if not hasattr(self, "editor_font"):
            self.editor_font = editor.font()
        editor.setFont(self.editor_font)
        editor.setMarginsFont(self.editor_font)
        index = self.tabs.addTab(editor, editor.title)
        pin = QToolButton()
        pin.setIcon(QIcon(str(Path(__file__).parent / "icons" / "pin.svg")))
        pin.setToolTip("Pin tab")
        pin.setAccessibleName("Pin tab")
        pin.setFixedSize(22, 22)
        pin.setAutoRaise(True)
        pin.clicked.connect(lambda: self.toggle_pin(editor, pin))
        self.tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.LeftSide, pin)
        close = QToolButton()
        close.setIcon(QIcon(str(Path(__file__).parent / "icons" / "close.svg")))
        close.setFixedSize(22, 22)
        close.setToolTip("Close tab")
        close.setAccessibleName("Close tab")
        close.clicked.connect(lambda: self.close_tab(self.tabs.indexOf(editor)))
        self.tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, close)
        editor.modificationChanged.connect(self.refresh)
        editor.cursorPositionChanged.connect(self.refresh)
        editor.textChanged.connect(self.refresh)
        self.tabs.setCurrentIndex(index)
        self.refresh()
        editor.setFocus()

    def new_document(self):
        self.untitled_count += 1
        editor = self.create_editor()
        editor.title = "Untitled Document" + (f" {self.untitled_count}" if self.untitled_count > 1 else "")
        self.add_editor(editor)

    def create_editor(self):
        return Editor()

    def create_tabbar(self):
        return Tabs()

    def new_window(self):
        child = Window()
        child.show()

    def toggle_pin(self, editor, button):
        editor.pinned = not editor.pinned
        button.setIcon(QIcon(str(Path(__file__).parent / "icons" / ("pin-filled.svg" if editor.pinned else "pin.svg"))))
        button.setToolTip("Unpin tab" if editor.pinned else "Pin tab")
        button.setAccessibleName(button.toolTip())
        index = self.tabs.indexOf(editor)
        close = self.tabs.tabBar().tabButton(index, QTabBar.ButtonPosition.RightSide)
        if close:
            close.setVisible(not editor.pinned)

    def refresh(self, *_):
        if not hasattr(self, "position"):
            return
        for index in range(self.tabs.count()):
            editor = self.tabs.widget(index)
            self.tabs.setTabText(index, ("*" if editor.isModified() else "") + editor.title)
            self.tabs.setTabToolTip(index, str(editor.path or editor.title))
        editor = self.editor()
        if editor:
            line, column = editor.getCursorPosition()
            self.position.setText(f"Ln {line + 1}, Col {column + 1}")
            self.mode.setText("OVR" if editor.overwriteMode() else "INS")
            self.tab_width.blockSignals(True)
            self.tab_width.setCurrentIndex([2, 4, 8].index(editor.tabWidth()))
            self.tab_width.blockSignals(False)

    def fill_recent(self):
        self.recent_menu.clear()
        for path in self.recent:
            action = self.recent_menu.addAction(("Folder: " if path.is_dir() else "File: ") + path.name)
            action.setToolTip(str(path))
            action.triggered.connect(lambda checked=False, p=path: self.open_path(p))
        if not self.recent:
            self.recent_menu.addAction("No recent items").setEnabled(False)

    def remember(self, path):
        self.recent = [path] + [p for p in self.recent if p != path][:19]

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Open", str(self.workspace or Path.home()))
        for path in paths:
            self.open_path(Path(path))

    def open_path(self, path):
        path = Path(path).resolve()
        if path.is_dir():
            self.set_folder(path)
            return
        for index in range(self.tabs.count()):
            if self.tabs.widget(index).path == path:
                self.tabs.setCurrentIndex(index)
                self.remember(path)
                return
        editor = self.create_editor()
        try:
            editor.load(path)
        except (OSError, UnicodeError, ValueError) as error:
            editor.deleteLater()
            self.report(f"Could not open {path.name}", error)
            return
        self.add_editor(editor)
        self.remember(path)

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Open Workspace", str(self.workspace or Path.home()))
        if path:
            self.set_folder(Path(path).resolve())

    def set_folder(self, path):
        # Prototype: browse only. Folder-scoped sessions are intentionally deferred.
        self.workspace = path
        self.tree.setRootIndex(self.model.setRootPath(str(path)))
        self.sidebar_title.setText(path.name)
        self.sidebar_title.setToolTip(str(path))
        self.sidebar.show()
        self.remember(path)

    def close_folder(self):
        self.workspace = None
        self.sidebar.hide()
        self.sidebar_title.setText("Files")

    def toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
        else:
            if not self.workspace:
                self.tree.setRootIndex(self.model.setRootPath(str(Path.home())))
            self.sidebar.show()

    def open_tree(self, index):
        if not self.model.isDir(index):
            self.open_path(Path(self.model.filePath(index)))

    def save_current(self):
        return self.save_editor(self.editor())

    def save_as(self):
        return self.save_editor(self.editor(), as_new=True)

    def save_all(self):
        for index in range(self.tabs.count()):
            editor = self.tabs.widget(index)
            if editor.isModified() and not self.save_editor(editor):
                return False
        return True

    def save_editor(self, editor, as_new=False):
        if editor is None:
            return False
        path = editor.path
        if path is None or as_new:
            filename, _ = QFileDialog.getSaveFileName(self, "Save As", str(path or (self.workspace or Path.home()) / editor.title))
            if not filename:
                return False
            path = Path(filename).resolve()
        for index in range(self.tabs.count()):
            other = self.tabs.widget(index)
            if other is not editor and other.path == path:
                self.report("Could not save", ValueError("This file is already open in another tab."))
                return False
        try:
            if path == editor.path and path.exists() and path.read_bytes() != editor.disk_bytes:
                answer = QMessageBox.question(self, "File changed on disk", "The file was changed by another application. Overwrite it?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    return False
            data = editor.encoded()
            output = QSaveFile(str(path))
            if not output.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(output.errorString())
            if output.write(data) != len(data):
                output.cancelWriting()
                raise OSError(output.errorString())
            if not output.commit():
                raise OSError(output.errorString())
        except (OSError, UnicodeError) as error:
            self.report(f"Could not save {path.name}", error)
            return False
        editor.path, editor.title, editor.disk_bytes = path, path.name, data
        editor.setModified(False)
        self.remember(path)
        self.refresh()
        return True

    def confirm_close(self, editor):
        if not editor.isModified():
            return True
        answer = QMessageBox.warning(self, "Unsaved changes", f"Save changes to {editor.title}?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Save)
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save_editor(editor)
        return True

    def close_current(self):
        self.close_tab(self.tabs.currentIndex())

    def close_tab(self, index):
        editor = self.tabs.widget(index)
        if editor is None or editor.pinned or not self.confirm_close(editor):
            return
        self.tabs.removeTab(index)
        editor.deleteLater()
        if not self.tabs.count():
            self.new_document()

    def closeEvent(self, event):
        for index in range(self.tabs.count()):
            if not self.confirm_close(self.tabs.widget(index)):
                event.ignore()
                return
        self.windows.remove(self)
        event.accept()

    def change_tab_width(self, index):
        if self.editor():
            self.editor().setTabWidth([2, 4, 8][index])

    def show_find(self):
        self.find_bar.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def find_next(self):
        if self.editor() and self.find_input.text():
            self.editor().findFirst(self.find_input.text(), False, False, False, True)

    def preferences(self):
        font, ok = QFontDialog.getFont(self.editor().font(), self, "Editor Font")
        if ok:
            self.editor_font = font
            for index in range(self.tabs.count()):
                editor = self.tabs.widget(index)
                editor.setFont(font)
                editor.setMarginsFont(font)

    def help(self):
        QMessageBox.information(self, "Editing", "Hold Alt and drag to select a rectangle. Type, copy, cut or paste in the selection; Escape exits block mode.\n\nCtrl+N/O/S/W: New/Open/Save/Close. Ctrl+F: Find. F9: Sidebar.\n\nThis prototype has no automatic recovery yet. Save documents before leaving them.")

    def about(self):
        QMessageBox.information(self, "About nex-editg", f"nex-editg {APP_VERSION} interface prototype\nQt 6 Widgets + QScintilla\nIndependent from the legacy gedit installation.\n\nWorkspace sessions and recovery await interface review.")

    def report(self, title, error):
        QMessageBox.critical(self, title, str(error))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--preview", help="Render the application client area to a PNG and exit")
    parser.add_argument("--capture", help="Render the application client area to a PNG and keep running")
    parser.add_argument("--data-dir", help="Use a separate settings/recovery directory (for testing)")
    args = parser.parse_args()
    app = QApplication([sys.argv[0]])
    app.setOrganizationName("Greenfinch628")
    app.setApplicationName("gedit-qt-prototype")
    app.setApplicationDisplayName("nex-editg")
    app.setDesktopFileName("com.greenfinch628.gedit.qtprototype")
    font = QFont("Cantarell")
    font.setPixelSize(17)
    app.setFont(font)
    app.setStyleSheet(STYLE)
    from enhancements import launch
    windows, lock = launch(app, transient=bool(args.preview), root_override=args.data_dir, paths=args.paths)
    if not windows:
        return 0
    window = windows[0]
    for path in args.paths:
        window.open_path(Path(path))
    window.show()
    if args.preview or args.capture:
        def capture():
            window.grab().save(args.preview or args.capture)
            if args.preview:
                app.quit()
        QTimer.singleShot(700, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
