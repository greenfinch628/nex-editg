"""Independent tab palettes, transactional edits, and session/workspace migration."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QDialog, QColorDialog
from enhancements import AppWindow, Store, TabColorDialog, tab_background, tab_color_palette, tab_foreground

app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    store = Store(Path(directory) / 'state')
    window = AppWindow(store)
    editor = window.editor()
    editor.tab_color = '#123456'
    record = window.snapshot()
    record["documents"][0].pop("inactive_color")
    restored = AppWindow(store, record=record)
    assert restored.editor().inactive_tab_color == '#123456'
    print('PASS: legacy explicit color preserved for both states')
    dialog = TabColorDialog('#123456', inactive='#fedcba')
    dialog.show(); app.processEvents()
    assert dialog.width() < 900 and dialog.height() < 500
    for palette in (dialog.active_palette, dialog.inactive_palette):
        assert len(palette.swatches) >= sum(map(len, tab_color_palette())) + 4
        assert sum(b.isChecked() for b in palette.swatches) == 1
        assert all(b.isVisible() for b in palette.swatches)
    dialog.grab().save('/tmp/nex-editg-tab-colors.png')
    inactive_before = dialog.inactive_palette.selected_color.name()
    QTest.mouseClick(dialog.active_palette.swatches[20], Qt.MouseButton.LeftButton)
    assert dialog.inactive_palette.selected_color.name() == inactive_before
    assert dialog.active_palette.swatches[20].isChecked()
    with patch.object(QColorDialog, 'getColor', return_value=QColor()):
        previous = list(dialog.active_palette.custom_colors)
        dialog.active_palette.custom_color()
        assert dialog.active_palette.custom_colors == previous
    before = window.document_record(editor)
    def cancel(d):
        d.active_palette.select_color(QColor('#abcdef'))
        with patch.object(QColorDialog, 'getColor', return_value=QColor('#987654')):
            d.inactive_palette.custom_color()
        return QDialog.DialogCode.Rejected
    with patch.object(TabColorDialog, 'exec', cancel):
        window.choose_tab_color(0)
    assert window.document_record(editor) == before
    def accept(d):
        with patch.object(QColorDialog, 'getColor', return_value=QColor('#102030')):
            d.active_palette.custom_color()
        assert d.inactive_palette.selected_color.name() != '#102030'
        with patch.object(QColorDialog, 'getColor', return_value=QColor('#f0e0d0')):
            d.inactive_palette.custom_color()
        assert '#102030' not in d.inactive_palette.custom_colors
        assert '#f0e0d0' not in d.active_palette.custom_colors
        assert all(sum(b.isChecked() for b in p.swatches) == 1 for p in (d.active_palette,d.inactive_palette))
        return QDialog.DialogCode.Accepted
    with patch.object(TabColorDialog, 'exec', accept):
        window.choose_tab_color(0)
    assert (editor.tab_color, editor.inactive_tab_color) == ('#102030', '#f0e0d0')
    print(f'PASS: {dialog.width()}x{dialog.height()} dialog, complete visible palettes, checkmarks, independent custom colors, Cancel/Select')
    window.new_document()
    second = window.editor()
    second.tab_color, second.inactive_tab_color = '#ffffff', '#000000'
    workspace = Path(directory) / 'workspace'; workspace.mkdir()
    window.workspace = workspace
    assert window.persist()
    identity = window.identity
    window.close()
    child = """
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from enhancements import AppWindow, Store
app = QApplication([])
store = Store(Path(sys.argv[1]))
w = AppWindow(store, sys.argv[2], store.load(store.window_path(sys.argv[2])))
assert w.tabs.widget(0).tab_color == '#102030'
assert w.tabs.widget(0).inactive_tab_color == '#f0e0d0'
assert '#102030' in w.tabs.widget(0).active_custom_colors
assert w.tabs.widget(1).tab_color == '#ffffff'
w.close()
"""
    subprocess.run([sys.executable, '-c', child, str(store.root), identity], check=True)
    # Recreate from on-disk session, just as application startup does.
    record = store.load(store.window_path(identity))
    reopened = AppWindow(store, identity, record)
    for i, expected in enumerate((('#102030','#f0e0d0'),('#ffffff','#000000'))):
        reopened.tabs.setCurrentIndex(i); app.processEvents()
        doc = reopened.tabs.widget(i)
        assert (tab_background(doc,reopened.options,True),tab_background(doc,reopened.options,False)) == expected
    assert '#102030' in reopened.tabs.widget(0).active_custom_colors
    assert '#f0e0d0' in reopened.tabs.widget(0).inactive_custom_colors
    folder_record = store.load(store.folder_path(identity,workspace))
    folder = AppWindow(store, record=folder_record)
    assert folder.tabs.widget(0).inactive_tab_color == '#f0e0d0'
    assert folder.tabs.widget(1).tab_color == '#ffffff'
    reopened.show(); app.processEvents(); reopened.grab()
    assert tab_foreground('#ffffff') == '#000000' and tab_foreground('#000000') == '#ffffff'
    print('PASS: multiple opposite color combinations, switching/rendering, disk restart and workspace restore, saved custom colors, contrast')
    folder.close(); reopened.close(); restored.close(); dialog.close()
