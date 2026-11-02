# -*- coding: utf-8 -*-
"""
Capture clean, high-resolution screenshots for README documentation with native font rendering.
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

sys.path.insert(0, os.path.abspath("."))

def main():
    # Make sure offscreen is NOT set
    if "QT_QPA_PLATFORM" in os.environ:
        del os.environ["QT_QPA_PLATFORM"]

    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))

    from src.core.i18n import i18n
    i18n.set_language("zh")

    docs_images = Path("docs/images")
    docs_images.mkdir(parents=True, exist_ok=True)

    from src.gui.custom_wire_dialog import CustomWireLibraryDialog, CustomWireEditorDialog, CloudWireSyncDialog
    from src.gui.wire_catalog_dialog import WireCatalogDialog
    from src.core.wire_catalog import get_custom_wire_manager, HUAYE_COPPER_CATALOG

    # 1. Custom Wire Catalog Dialog
    print("Capturing custom_wire_catalog_dialog...")
    dlg1 = CustomWireLibraryDialog(current_diameter=0.170)
    dlg1.resize(1020, 640)
    dlg1.show()
    app.processEvents()
    pix1 = dlg1.grab()
    p1 = docs_images / "custom_wire_catalog_dialog.png"
    pix1.save(str(p1), "PNG")
    print(f"Saved {p1} ({p1.stat().st_size} bytes)")
    dlg1.close()

    # 2. Custom Wire Editor Dialog
    print("Capturing custom_wire_editor_dialog...")
    mgr = get_custom_wire_manager()
    wires = mgr.list_all()
    sample_wire = wires[0] if wires else None
    dlg2 = CustomWireEditorDialog(wire_item=sample_wire)
    dlg2.resize(720, 760)
    dlg2.show()
    app.processEvents()
    pix2 = dlg2.grab()
    p2 = docs_images / "custom_wire_editor_dialog.png"
    pix2.save(str(p2), "PNG")
    print(f"Saved {p2} ({p2.stat().st_size} bytes)")
    dlg2.close()

    # 3. Cloud Wire Sync Dialog
    print("Capturing cloud_wire_sync_dialog...")
    dlg3 = CloudWireSyncDialog(manager=mgr)
    dlg3.resize(680, 520)
    dlg3.show()
    app.processEvents()
    pix3 = dlg3.grab()
    p3 = docs_images / "cloud_wire_sync_dialog.png"
    pix3.save(str(p3), "PNG")
    print(f"Saved {p3} ({p3.stat().st_size} bytes)")
    dlg3.close()

    # 4. Flat Wire Huaye Standards Preview
    print("Capturing flat_wire_huaye_standards_preview...")
    dlg4 = WireCatalogDialog(current_diameter=0.170, is_ccaw=False)
    dlg4.resize(960, 600)
    dlg4.show()
    app.processEvents()
    pix4 = dlg4.grab()
    p4 = docs_images / "flat_wire_huaye_standards_preview.png"
    pix4.save(str(p4), "PNG")
    print(f"Saved {p4} ({p4.stat().st_size} bytes)")
    dlg4.close()

    print("All screenshots captured cleanly!")
    os._exit(0)

if __name__ == "__main__":
    main()
