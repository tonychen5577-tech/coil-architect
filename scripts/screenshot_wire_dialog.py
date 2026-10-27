# -*- coding: utf-8 -*-
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.abspath("."))
from PyQt6.QtWidgets import QApplication

def main():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    out_dir = Path(r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b")
    
    from src.core.i18n import i18n
    from src.gui.wire_catalog_dialog import WireCatalogDialog
    from src.gui.main_window import MainWindow
    
    i18n.set_language("zh")
    
    # 1. Capture WireCatalogDialog
    dlg = WireCatalogDialog(current_diameter=0.170, is_ccaw=False)
    dlg.resize(760, 540)
    dlg.show()
    app.processEvents()
    
    pix_dlg = dlg.grab()
    path_dlg = out_dir / "ui_wire_catalog_dialog.png"
    pix_dlg.save(str(path_dlg), "PNG")
    print("Saved dialog screenshot:", path_dlg)
    dlg.close()
    
    # 2. Capture MainWindow with chosen wire & 5 Huaye materials
    mw = MainWindow()
    mw.resize(1380, 860)
    mw.show()
    
    # Apply a chosen wire
    from src.core.wire_catalog import HUAYE_COPPER_CATALOG
    wire = HUAYE_COPPER_CATALOG[9] # 0.170mm
    mw._apply_catalog_wire(wire)
    mw.run_simulation()
    app.processEvents()
    
    pix_mw = mw.grab()
    path_mw = out_dir / "ui_main_window_wire_catalog.png"
    pix_mw.save(str(path_mw), "PNG")
    print("Saved main window screenshot:", path_mw)
    mw.close()

if __name__ == "__main__":
    main()
