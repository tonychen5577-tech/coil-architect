# -*- coding: utf-8 -*-
import sys
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.gui.incoming_wire_dialog import IncomingWireDialog
from src.gui.wire_catalog_dialog import WireCatalogDialog

app = QApplication.instance() or QApplication(sys.argv)
art_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"

# 1. Main Window Screenshot
window = MainWindow()
window.resize(1380, 880)
window.show()
app.processEvents()
pix_main = window.grab()
path_main = os.path.join(art_dir, "ui_incoming_wire_button.png")
pix_main.save(path_main, "PNG")
print("Saved ui_incoming_wire_button.png")

# 2. Incoming Wire Dialog Screenshot
dlg = IncomingWireDialog(current_bare_dia=0.045, current_max_od=0.055, current_rm=10.747, current_km_kg=70.620)
dlg.show()
app.processEvents()
pix_dlg = dlg.grab()
path_dlg = os.path.join(art_dir, "ui_incoming_wire_dialog.png")
pix_dlg.save(path_dlg, "PNG")
print("Saved ui_incoming_wire_dialog.png")
dlg.close()

# 3. Wire Catalog Dialog Screenshot
catalog_dlg = WireCatalogDialog(current_diameter=0.080)
catalog_dlg.show()
app.processEvents()
pix_cat = catalog_dlg.grab()
path_cat = os.path.join(art_dir, "ui_wire_catalog_dialog_simplified.png")
pix_cat.save(path_cat, "PNG")
print("Saved ui_wire_catalog_dialog_simplified.png")
catalog_dlg.close()

window.close()
