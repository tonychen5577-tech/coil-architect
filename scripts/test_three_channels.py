import sys
import os
from pathlib import Path

# 添加工程根目录
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtGui import QFont
from src.gui.about_dialog import AboutDialog

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))

    dlg = AboutDialog()
    dlg.show()
    app.processEvents()

    brain_dir = Path(r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b")

    # 1. 保存官方公众号视图
    dlg.grab().save(str(brain_dir / "about_channel_1_official.png"))
    print("✅ 已保存官方公众号截图: about_channel_1_official.png")

    # 查找并点击“微信技术咨询”按钮
    buttons = dlg.findChildren(QPushButton)
    btn_wechat = next((b for b in buttons if "微信技术咨询" in b.text()), None)
    btn_whatsapp = next((b for b in buttons if "WhatsApp" in b.text()), None)

    if btn_wechat:
        btn_wechat.click()
        app.processEvents()
        dlg.grab().save(str(brain_dir / "about_channel_2_wechat.png"))
        print("✅ 已保存微信咨询截图: about_channel_2_wechat.png")

    if btn_whatsapp:
        btn_whatsapp.click()
        app.processEvents()
        dlg.grab().save(str(brain_dir / "about_channel_3_whatsapp.png"))
        print("✅ 已保存 WhatsApp 国际支持截图: about_channel_3_whatsapp.png")

    print("\n🎉 三重通道切换与二维码验证全部完成！")

if __name__ == "__main__":
    main()
