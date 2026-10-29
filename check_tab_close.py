"""Tab close decisions and independent app-close recovery regression checks."""
from pathlib import Path
import tempfile
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from enhancements import AppWindow, Store

app = QApplication([])
buttons = QMessageBox.StandardButton
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    store = Store(root / 'state')
    window = AppWindow(store)
    for named in (False, True):
        if named:
            path = root / 'named.txt'
            path.write_text('original')
            window.open_path(path)
        else:
            window.new_document()
        editor = window.editor()
        editor.setText('changed text')
        editor.setModified(True)
        index = window.tabs.indexOf(editor)
        with patch.object(QMessageBox, 'warning', return_value=buttons.Cancel) as prompt:
            editor.close_button.click()
            prompt.assert_called_once()
            assert window.tabs.indexOf(editor) == index and editor.isModified()
        with patch.object(QMessageBox, 'warning', return_value=buttons.Save), patch.object(window, 'save_editor', return_value=False):
            window.close_tab(index)
            assert window.tabs.indexOf(editor) == index
        if not named:
            with patch.object(QMessageBox, 'warning', return_value=buttons.Save), patch.object(QFileDialog, 'getSaveFileName', return_value=('', '')):
                window.close_tab(index)
                assert window.tabs.indexOf(editor) == index
        destination = root / ('named.txt' if named else 'saved-draft.txt')
        with patch.object(QMessageBox, 'warning', return_value=buttons.Save), patch.object(QFileDialog, 'getSaveFileName', return_value=(str(destination), '')):
            window.close_tab(index)
            assert window.tabs.indexOf(editor) == -1
            assert destination.read_text() == 'changed text'
        window.new_document()
        draft = window.editor()
        draft.setText('discarded draft')
        draft.setModified(True)
        with patch.object(QMessageBox, 'warning', return_value=buttons.Discard):
            window.close_tab(window.tabs.indexOf(draft))
            assert window.tabs.indexOf(draft) == -1
    window.new_document()
    draft = window.editor()
    draft.setText('session draft')
    draft.setModified(True)
    identity = window.identity
    with patch.object(QMessageBox, 'warning', side_effect=AssertionError('app close prompted')), patch.object(QMessageBox, 'exec', side_effect=AssertionError('app close prompted')):
        assert window.close()
    restored = AppWindow(store, identity, store.load(store.window_path(identity)))
    assert restored.editor().text() == 'session draft'
    assert restored.editor().isModified()
    assert restored.close()
print('PASS: named/unnamed tab Save, Discard, Cancel; save failure/cancellation; close button; app-close session recovery')
