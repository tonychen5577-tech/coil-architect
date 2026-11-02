# -*- coding: utf-8 -*-
"""
Generate screenshot artifacts of Custom Wire Library, Editor, and GB Unit Wire Catalog.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath("."))

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.gui.main_window import MainWindow
from src.gui.custom_wire_dialog import CustomWireLibraryDialog, CustomWireEditorDialog
from src.gui.wire_catalog_dialog import WireCatalogDialog

artifacts_dir = Path(r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b")

win = MainWindow()
win.resize(1380, 880)
win.show()
app.processEvents()

# 1. Capture Main Window with Custom Wire applied
from src.core.wire_catalog import get_custom_wire_manager
mgr = get_custom_wire_manager()
first_wire = mgr.list_all()[0]
win._apply_custom_wire(first_wire)
app.processEvents()
pix_main = win.grab()
pix_main.save(str(artifacts_dir / "ui_custom_wire_main_window.png"))
print("Saved ui_custom_wire_main_window.png")

# 2. Capture Custom Wire Library Dialog
dlg_lib = CustomWireLibraryDialog(current_diameter=0.080, parent=win)
dlg_lib.resize(1020, 620)
dlg_lib.show()
app.processEvents()
pix_lib = dlg_lib.grab()
pix_lib.save(str(artifacts_dir / "ui_custom_wire_library_dialog.png"))
print("Saved ui_custom_wire_library_dialog.png")
dlg_lib.close()

# 3. Capture Custom Wire Editor Dialog (showing mutual derivation between % IACS and Rm)
dlg_edit = CustomWireEditorDialog(wire_item=first_wire, parent=win)
dlg_edit.resize(700, 750)
dlg_edit.show()
app.processEvents()
pix_edit = dlg_edit.grab()
pix_edit.save(str(artifacts_dir / "ui_custom_wire_editor_dialog.png"))
print("Saved ui_custom_wire_editor_dialog.png")
dlg_edit.close()

# 4. Capture Wire Catalog Dialog showing GB Units (m/kg and Ohm/m) and Custom Catalog button
dlg_cat = WireCatalogDialog(current_diameter=0.080, parent=win)
dlg_cat.resize(920, 580)
dlg_cat.show()
app.processEvents()
pix_cat = dlg_cat.grab()
pix_cat.save(str(artifacts_dir / "ui_wire_catalog_gb_units.png"))
print("Saved ui_wire_catalog_gb_units.png")
dlg_cat.close()

win.close()
print("All screenshots generated successfully!")
os._exit(0)
