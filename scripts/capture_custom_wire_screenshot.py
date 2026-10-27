# -*- coding: utf-8 -*-
"""
Capture screenshot of MainWindow with custom wire 0.045 bare / 0.055 outer diameter.
"""
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.gui.main_window import MainWindow

def capture():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    window.resize(1380, 880)
    window.show()

    # Set custom 0.045 bare / 0.055 outer
    window.sb_bare_dia.setValue(0.045)
    window.sb_max_od.setValue(0.055)

    app.processEvents()

    art_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    save_path = os.path.join(art_dir, "ui_custom_wire_od_stability.png")
    pixmap = window.grab()
    pixmap.save(save_path, "PNG")
    print(f"Screenshot saved to: {save_path}")

    window.close()

if __name__ == "__main__":
    capture()
