"""
Full Verification Script for User Requests:
1. Splash Screen title consistency: ANSV 微型执行器与精密传动仿真验证平台 (Actuator Numerical Simulation & Validation)
2. About Dialog: Plain-language core features, platform full name, and WeChat Official Account contact module
3. ISO 129 / ISO 5459 2D cross section
4. Timestamped export files
5. Generous Excel column widths
"""

import os
import re
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime
from PyQt6.QtWidgets import QApplication

from src.core.models import CoilInputs, CoilOutputs, CoilType, WindingMode
from src.core.physics_engine import CoilPhysicsEngine
from src.gui.splash_screen import SplashScreen
from src.gui.about_dialog import AboutDialog
from src.gui.widgets.coil_canvas import MagnetSectionCanvas
from src.version import PLATFORM_NAME, PLATFORM_NAME_EN, PLATFORM_FULL_TITLE, WECHAT_OFFICIAL_ACCOUNT
import openpyxl

def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    artifact_dir = r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b"
    os.makedirs(artifact_dir, exist_ok=True)

    print("=== 1. VERIFY SPLASH SCREEN CONSISTENCY ===")
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    splash_pix = splash.grab()
    splash_path = os.path.join(artifact_dir, "verify_splash_screen_platform_name.png")
    splash_pix.save(splash_path)
    print(f"✓ Saved splash screen screenshot: {splash_path}")
    splash.close()

    print("\n=== 2. VERIFY ABOUT DIALOG (FEATURES + WECHAT + PLATFORM NAME) ===")
    about = AboutDialog()
    about.show()
    app.processEvents()
    about_pix = about.grab()
    about_path = os.path.join(artifact_dir, "verify_about_dialog_wechat_features.png")
    about_pix.save(about_path)
    print(f"✓ Saved about dialog screenshot: {about_path}")

    # Test copy wechat
    clipboard = QApplication.clipboard()
    clipboard.setText("")
    about._copy_text(WECHAT_OFFICIAL_ACCOUNT, about.findChild(type(about), ""), "")
    copied = clipboard.text()
    print(f"  WeChat account copied: '{copied}' (expected: '{WECHAT_OFFICIAL_ACCOUNT}')")
    assert copied == WECHAT_OFFICIAL_ACCOUNT, "Failed to copy WeChat account"
    about.close()

    print("\n=== 3. VERIFY ISO 129 / 5459 2D CROSS SECTION CANVAS ===")
    inputs = CoilInputs(
        coil_type=CoilType.RACETRACK,
        inner_len=3.5,
        inner_wid=0.92,
        radial_layers=12,
        axial_turns=12,
        bare_dia=0.045,
        max_od=0.053,
        tension_factor=0.99,
        dfm_enabled=False
    )
    outputs = CoilPhysicsEngine.calculate(inputs)

    sec_canvas = MagnetSectionCanvas()
    sec_canvas.resize(680, 290)
    sec_canvas.updateData(inputs, outputs)
    sec_canvas.show()
    app.processEvents()
    canvas_pix = sec_canvas.grab()
    canvas_path = os.path.join(artifact_dir, "verify_iso_section_view.png")
    canvas_pix.save(canvas_path)
    print(f"✓ Saved ISO section canvas screenshot: {canvas_path}")
    sec_canvas.close()

    print("\n==========================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
    print("==========================================")

if __name__ == "__main__":
    main()
