"""Focused default/shared tab color and persistence checks."""
import tempfile
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtGui import QColor
from enhancements import AppWindow, Store, TabColorDialog, tab_background
app = QApplication([])
def colors(w, i=0):
    return tuple(tab_background(w.tabs.widget(i), w.options, active) for active in (True, False))
def select(dialog):
    dialog.active_palette.select_color(QColor('#123456'))
    dialog.inactive_palette.select_color(QColor('#abcdef'))
    return QDialog.DialogCode.Accepted
with tempfile.TemporaryDirectory() as directory:
    store = Store(Path(directory))
    w = AppWindow(store)
    other = AppWindow(store)
    original = colors(w)
    assert original == (store.settings['active_color'], store.settings['inactive_color'])
    values = dict(w.options, active_color='#334455', inactive_color='#ddeeff')
    store.save_settings(values)
    w.options = values
    w.apply_options()
    assert colors(w) == original
    assert w.document_record(w.tabs.widget(0))['color'] is None
    w.new_document()
    assert colors(w, 1) == ('#334455', '#ddeeff')
    with patch.object(TabColorDialog, 'exec', select):
        w.choose_tab_color(0)
        assert colors(w) == ('#123456', '#abcdef')
        assert colors(w, 1) == ('#334455', '#ddeeff')
        w.choose_tab_color(0, all_tabs=True)
    assert colors(other) == original
    assert store.settings['active_color'] == '#334455'
    w.new_document()
    assert all(colors(w, i) == ('#123456', '#abcdef') for i in range(3))
    before = w.snapshot()
    with patch.object(TabColorDialog, 'exec', return_value=QDialog.DialogCode.Rejected):
        w.choose_tab_color(0, all_tabs=True)
    assert w.snapshot()['documents'] == before['documents']
    assert w.shared_tab_colors == ('#123456', '#abcdef')
    w.reset_tab_color(0)
    assert colors(w) == ('#334455', '#ddeeff')
    assert colors(w, 1) == ('#123456', '#abcdef')
    workspace = Path(directory) / 'workspace'
    workspace.mkdir()
    w.workspace = workspace
    assert w.persist()
    # New Store and window read the actual on-disk session and Preferences.
    restarted_store = Store(Path(directory))
    for record in (store.load(store.window_path(w.identity)), store.load(store.folder_path(w.identity, workspace))):
        restored = AppWindow(restarted_store, record=record)
        assert colors(restored) == ('#334455', '#ddeeff')
        assert colors(restored, 1) == ('#123456', '#abcdef')
        restored.new_document()
        assert colors(restored, 3) == ('#123456', '#abcdef')
        restored.reset_tab_color(0, all_tabs=True)
        assert restored.shared_tab_colors is None
        assert all(colors(restored, i) == ('#334455', '#ddeeff') for i in range(4))
        restored.new_document()
        assert colors(restored, 4) == ('#334455', '#ddeeff')
        assert all(d['color'] is None and d['inactive_color'] is None for d in restored.snapshot()['documents'])
        restored.close()
    w.close(); other.close()
print('PASS: stable existing defaults, new defaults, individual/shared/reset priority, window isolation, Cancel, disk session/workspace restore, no duplicated defaults')
