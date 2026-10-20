"""
Verify final MainWindow and canvases
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from src.gui.main_window import MainWindow

def test_final():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1380, 860)
    win.show()

    # 1. 验证微观剖面 3 档切换
    micro = win.canvas_widget.micro_canvas

    # Z-X 截面 (看X边界)
    micro.view_mode = "zx"
    micro.update()
    app.processEvents()
    pix = QPixmap(win.size())
    win.render(pix)
    pix.save("verify_final_zx.png")

    # Z-Y 截面 (看Y边界)
    micro.view_mode = "zy"
    micro.update()
    app.processEvents()
    pix = QPixmap(win.size())
    win.render(pix)
    pix.save("verify_final_zy.png")

    # Tab 2: VCM 径向磁路与顶盖限高剖面
    tab_widget = win.canvas_widget.tab_macro
    tab_widget.setCurrentIndex(1)
    app.processEvents()
    pix = QPixmap(win.size())
    win.render(pix)
    pix.save("verify_final_magnet_vcm.png")

    print("All final verification snapshots saved successfully!")

if __name__ == "__main__":
    test_final()
