"""Isolation, recovery failures, preference and editing behavior checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox
from enhancements import AppWindow, DEFAULTS, EnhancedEditor, Preferences, Store
from editor import STYLE


def run():
    app = QApplication([])
    app.setStyleSheet(STYLE)
    with tempfile.TemporaryDirectory(prefix="gedit-next-check-") as directory:
        root = Path(directory)
        store = Store(root / "state")
        window = AppWindow(store)
        window.show()
        app.processEvents()
        editor = window.editor()
        assert editor.pin_button.isVisible() and editor.close_button.isVisible()
        editor.setText("unsaved café 🐦\nsecond line\n")
        editor.setModified(True)
        editor.setCursorPosition(1, 3)
        editor.tab_color = "#d4edda"
        editor.insert_spaces = True
        editor.setTabWidth(4)
        assert window.persist()
        identity = window.identity
        record = store.load(store.window_path(identity))
        assert record["documents"][0]["text"] == editor.text()
        assert os.stat(store.window_path(identity)).st_mode & 0o777 == 0o600
        assert os.stat(store.root).st_mode & 0o777 == 0o700
        with patch.object(QMessageBox, "question", side_effect=AssertionError("unexpected prompt")):
            assert window.close()
        restored = AppWindow(store, identity, record)
        restored.show()
        recovered = restored.editor()
        assert recovered.text() == "unsaved café 🐦\nsecond line\n"
        assert recovered.isModified() and recovered.tabWidth() == 4 and recovered.insert_spaces
        assert recovered.getCursorPosition() == (1, 3) and recovered.tab_color == "#d4edda"
        print("PASS: no-prompt close/reopen restores Unicode, dirty state, cursor, tab options and color; private file permissions")

        with patch.object(store, "save", side_effect=OSError("simulated full disk")), patch.object(QMessageBox, "critical"):
            assert not restored.confirm_close(recovered)
            restored.close_tab(0)
            assert restored.editor() is recovered
            assert not restored.close()
            assert recovered.text().startswith("unsaved")
        print("PASS: failed recovery prevents tab and window closure")

        assert restored.persist()
        closed_text = recovered.text()
        with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Discard):
            restored.close_tab(0)
        archives = list((store.root / "closed-tabs").glob("*.json"))
        assert len(archives) == 1
        assert json.loads(archives[0].read_text())["text"] == closed_text
        restored.restore_editor(json.loads(archives[0].read_text()))
        assert restored.editor().text() == closed_text
        print("PASS: explicit close archives the document and it can be restored")

        folder_a = root / "folder-a"
        folder_b = root / "folder-b"
        folder_a.mkdir(); folder_b.mkdir()
        restored.set_folder(folder_a)
        restored.editor().setText("first folder draft")
        restored.set_folder(folder_b)
        restored.editor().setText("second folder draft")
        restored.set_folder(folder_a)
        assert restored.editor().text() == "first folder draft"
        restored.close_folder()
        assert restored.editor().text() == closed_text
        assert not list(folder_a.iterdir()) and not list(folder_b.iterdir())
        print("PASS: independent folder sessions and loose documents survive switching without writing files inside folders")

        nested = folder_a / "nested"
        nested.mkdir()
        selected_file = nested / "selected.txt"
        selected_file.write_text("fixture")
        restored.set_folder(folder_a)
        QTest.qWait(180)
        nested_index = restored.model.index(str(nested))
        restored.tree.expand(nested_index)
        QTest.qWait(150)
        restored.tree.setCurrentIndex(restored.model.index(str(selected_file)))
        assert restored.persist()
        restored.set_folder(folder_b)
        restored.set_folder(folder_a)
        QTest.qWait(200)
        assert restored.tree.isExpanded(restored.model.index(str(nested)))
        assert restored.model.filePath(restored.tree.currentIndex()) == str(selected_file)
        second_window = AppWindow(store)
        second_window.show()
        second_window.set_folder(folder_a)
        assert second_window.editor().text() == "first folder draft"
        assert folder_a in second_window.recent
        print("PASS: workspace tree expansion/selection restore and new windows reopen the shared folder session")
        restored.close_folder()

        path = root / "file.txt"
        path.write_text("original disk")
        restored.open_path(path)
        restored.editor().setText("unsaved edit")
        restored.editor().setModified(True)
        assert restored.persist()
        snapshot = store.load(store.window_path(identity))
        path.write_text("external edit")
        reopened = AppWindow(store, record=snapshot)
        assert reopened.editor().text() == "unsaved edit"
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            assert not reopened.save_current()
        assert path.read_text() == "external edit"
        print("PASS: recovered edits never overwrite originals; saving detects external changes")

        current_path = store.window_path(reopened.identity)
        reopened.editor().append("newer snapshot")
        assert reopened.persist()
        current_path.write_text("broken JSON")
        previous = store.load(current_path)
        assert previous["documents"]
        assert reopened.persist()
        assert list(current_path.parent.glob(current_path.stem + ".corrupt-*.json"))
        print("PASS: corrupt latest snapshot falls back, and its original bytes are archived before replacement")

        spell_editor = EnhancedEditor(dict(DEFAULTS, spell=True))
        spell_editor.show()
        spell_editor.setText("hello qzxqzx\n")
        spell_editor.check_spelling()
        assert spell_editor.dictionary is not None
        assert spell_editor.SendScintilla(spell_editor.SCI_INDICATORVALUEAT, spell_editor.spell_indicator, 6)
        spell_editor.options["spell"] = False
        spell_editor.check_spelling()
        assert not spell_editor.SendScintilla(spell_editor.SCI_INDICATORVALUEAT, spell_editor.spell_indicator, 6)
        spell_editor.options["spell"] = True
        spell_editor.setText("echo qzxqzx\n# qzxqzx\n")
        spell_editor.configure_language("Bash")
        spell_editor.check_spelling()
        assert not spell_editor.SendScintilla(spell_editor.SCI_INDICATORVALUEAT, spell_editor.spell_indicator, 5)
        assert spell_editor.SendScintilla(spell_editor.SCI_INDICATORVALUEAT, spell_editor.spell_indicator, 15)
        spell_editor.setText("```\nqzxqzx\n```\nqzxqzx\n")
        spell_editor.configure_language("Markdown")
        spell_editor.check_spelling()
        assert not spell_editor.SendScintilla(spell_editor.SCI_INDICATORVALUEAT, spell_editor.spell_indicator, 4)
        assert spell_editor.SendScintilla(spell_editor.SCI_INDICATORVALUEAT, spell_editor.spell_indicator, 15)
        print("PASS: optional spelling underlines prose and Bash comments, excludes shell code and Markdown fences")

        spell_editor.options["spell"] = False
        spell_editor.setText("a")
        spell_editor.configure_language("Plain Text")
        spell_editor.setCursorPosition(0, 1)
        spell_editor.setTabWidth(4)
        spell_editor.insert_spaces = True
        QTest.keyClick(spell_editor, Qt.Key.Key_Tab)
        assert spell_editor.text() == "a   "
        spell_editor.insert_spaces = False
        QTest.keyClick(spell_editor, Qt.Key.Key_Tab)
        assert spell_editor.text() == "a   \t"
        spell_editor.setText("abcd\nefgh\n")
        spell_editor.insert_spaces = True
        spell_editor.SendScintilla(spell_editor.SCI_SETRECTANGULARSELECTIONANCHOR, 1)
        spell_editor.SendScintilla(spell_editor.SCI_SETRECTANGULARSELECTIONCARET, spell_editor.positionFromLineIndex(1, 3))
        QTest.keyClick(spell_editor, Qt.Key.Key_Tab)
        assert spell_editor.text() == "a   d\ne   h\n"
        print("PASS: Tab inserts spaces to the next stop or a literal tab according to the bottom control")

        dialog = Preferences(restored)
        assert dialog.findChild(type(restored.tabs)).count() == 4
        settings = dict(DEFAULTS, spaces=True, tab_width=8, tab_px=14, editor_pt=11)
        store.save_settings(settings)
        assert Store(store.root).settings == settings
        assert restored.tabs.tabBar().tabSizeHint(0).height() == 34
        print("PASS: four preferences sections, persistent defaults and shorter tabs")

        reopened.new_document()
        pinned_editor = reopened.editor()
        pin_button = pinned_editor.pin_button
        reopened.toggle_pin(pinned_editor, pin_button)
        assert reopened.tabs.widget(0) is pinned_editor
        reopened.tabs.tabBar().moveTab(0, reopened.tabs.count() - 1)
        assert reopened.tabs.widget(0) is pinned_editor
        unpinned = reopened.tabs.widget(reopened.tabs.count() - 1)
        reopened.tabs.tabBar().moveTab(reopened.tabs.count() - 1, 0)
        assert reopened.tabs.widget(0) is pinned_editor and reopened.tabs.indexOf(unpinned) >= 1
        print("PASS: pinned tabs stay fixed and unpinned tabs cannot be dragged before them")

        reopened.new_document()
        replacement_editor = reopened.editor()
        replacement_editor.setText("Alpha alpha ALPHA\n")
        reopened.find_input.setText("alpha")
        reopened.replace_input.setText("café 🐦")
        reopened.case_control.setChecked(False)
        reopened.replace_all()
        assert replacement_editor.text() == "café 🐦 café 🐦 café 🐦\n"
        replacement_editor.undo()
        assert replacement_editor.text() == "Alpha alpha ALPHA\n"
        reopened.case_control.setChecked(True)
        reopened.replace_all()
        assert replacement_editor.text() == "Alpha café 🐦 ALPHA\n"
        print("PASS: literal Unicode Replace All, case selection and one-step undo")

        from git_browser import git_status
        git_root = root / "repository"
        git_root.mkdir()
        def git(*args):
            return subprocess.run(["git", "--no-pager", "-C", str(git_root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        git("init", "-q")
        (git_root / "nested").mkdir()
        tracked = git_root / "nested" / "file.txt"
        tracked.write_text("baseline")
        git("add", ".")
        git("-c", "user.name=Editor Check", "-c", "user.email=check@example.invalid", "commit", "-qm", "fixture")
        tracked.write_text("changed")
        unusual = git_root / "nested" / "new\nfile.txt"
        unusual.write_text("new")
        index_before = (git_root / ".git/index").read_bytes()
        status = git_status(git_root / "nested")
        assert status[str(tracked)] == "M" and status[str(unusual)] == "?"
        assert (git_root / ".git/index").read_bytes() == index_before
        assert git_status(root / "folder-a") == {}
        print("PASS: Git badges support nested roots and newline filenames without modifying the index")

        # Abrupt process exit after the debounce proves actual on-change recovery.
        crash_root = root / "crash-state"
        script = '''from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from enhancements import Store, AppWindow
import os,sys
a=QApplication([]); w=AppWindow(Store(sys.argv[1]),identity="crash")
w.editor().setText("recovered after process crash 🐦")
QTimer.singleShot(1000,lambda:os._exit(23)); a.exec()
'''
        child = subprocess.run([sys.executable, "-c", script, str(crash_root)], cwd=Path(__file__).parent, env=dict(os.environ, QT_QPA_PLATFORM="offscreen"), timeout=10)
        assert child.returncode == 23
        crash_record = Store(crash_root).load(crash_root / "windows" / "crash.json")
        assert crash_record["documents"][0]["text"] == "recovered after process crash 🐦"
        print("PASS: crash recovery includes debounced unsaved changes from a separate process")
        for candidate in list(AppWindow.windows):
            candidate.recovery_timer.stop()
    app.quit()


if __name__ == "__main__":
    run()
