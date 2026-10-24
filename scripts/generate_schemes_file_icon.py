"""
=============================================================================
Script: scripts/generate_schemes_file_icon.py
Description: 生成 ANSV Coil-Architect Pro 多方案对比集专属文件图标 (.ansvschemes)
与单工程文件 (.ansvcoil) 形成鲜明而统一的工业视觉区分：
- .ansvcoil (单算例): 浅蓝科技底衬 + 单一黄金微型线圈 + 深蓝「COIL」徽标
- .ansvschemes (多方案对比集): 浅绿/翡翠方案底衬 + 多个错落排列的对比线圈 (Scheme A/B/C) + 翡翠绿「SCHEMES」徽标
包含 7 层全金字塔自适应分辨率: 16, 24, 32, 48, 64, 128, 256
=============================================================================
"""

import sys
import os
import math
import struct
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import (
    QImage, QPainter, QColor, QLinearGradient, QRadialGradient,
    QPen, QBrush, QPainterPath, QFont
)
from PyQt6.QtCore import Qt, QPointF, QRectF

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


def draw_schemes_file_icon(size: int) -> QImage:
    """绘制指定尺寸的专属方案对比集文件图标 (.ansvschemes)"""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale = size / 256.0

    # 1. 经典工程文档几何轮廓 (带右上角 45° 优雅折角)
    left = 32.0 * scale
    top = 18.0 * scale
    right = 224.0 * scale
    bottom = 238.0 * scale
    corner = 52.0 * scale
    radius = 10.0 * scale

    # 主纸张路径
    doc_path = QPainterPath()
    doc_path.moveTo(left + radius, top)
    doc_path.lineTo(right - corner, top)
    doc_path.lineTo(right, top + corner)
    doc_path.lineTo(right, bottom - radius)
    doc_path.quadTo(right, bottom, right - radius, bottom)
    doc_path.lineTo(left + radius, bottom)
    doc_path.quadTo(left, bottom, left, bottom - radius)
    doc_path.lineTo(left, top + radius)
    doc_path.quadTo(left, top, left + radius, top)
    doc_path.closeSubpath()

    # 纸张投影
    if size >= 32:
        shadow_path = QPainterPath()
        s_off = 4.0 * scale
        shadow_path.moveTo(left + radius, top + s_off)
        shadow_path.lineTo(right - corner, top + s_off)
        shadow_path.lineTo(right + s_off, top + corner)
        shadow_path.lineTo(right + s_off, bottom - radius + s_off)
        shadow_path.quadTo(right + s_off, bottom + s_off, right - radius + s_off, bottom + s_off)
        shadow_path.lineTo(left + radius, bottom + s_off)
        shadow_path.quadTo(left, bottom + s_off, left, bottom - radius + s_off)
        shadow_path.closeSubpath()
        painter.fillPath(shadow_path, QColor(15, 23, 42, 35))

    # 纸张渐变底衬 (微带清亮翡翠工程矩阵感 #F0FDF4 -> #E2E8F0)
    paper_grad = QLinearGradient(0, top, 0, bottom)
    paper_grad.setColorAt(0.0, QColor("#FFFFFF"))
    paper_grad.setColorAt(0.65, QColor("#F0FDF4"))
    paper_grad.setColorAt(1.0, QColor("#E2E8F0"))

    painter.setPen(QPen(QColor("#86EFAC" if size >= 64 else "#94A3B8"), max(1.0, 3.0 * scale)))
    painter.setBrush(paper_grad)
    painter.drawPath(doc_path)

    # 2. 右上角折角区域 (Folded Flap)
    flap_path = QPainterPath()
    flap_path.moveTo(right - corner, top)
    flap_path.lineTo(right - corner, top + corner - (4.0 * scale))
    flap_path.quadTo(right - corner, top + corner, right - corner + (4.0 * scale), top + corner)
    flap_path.lineTo(right, top + corner)
    flap_path.closeSubpath()

    flap_grad = QLinearGradient(right - corner, top, right, top + corner)
    flap_grad.setColorAt(0.0, QColor("#BBF7D0"))
    flap_grad.setColorAt(0.5, QColor("#DCFCE7"))
    flap_grad.setColorAt(1.0, QColor("#FFFFFF"))

    painter.setPen(QPen(QColor("#86EFAC"), max(1.0, 2.5 * scale)))
    painter.setBrush(flap_grad)
    painter.drawPath(flap_path)

    # 3. 核心区域：绘制「多个线圈对比拓扑」 (左：八角线圈，中：双环同心，右：跑道线圈)
    # 后景方案矩阵分栏微网格 (体现比对抽屉 Matrix 列)
    if size >= 48:
        painter.save()
        painter.setPen(QPen(QColor("#CBD5E1"), max(0.8, 1.2 * scale), Qt.PenStyle.DashLine))
        div_x1 = left + (right - left) * 0.35
        div_x2 = left + (right - left) * 0.65
        painter.drawLine(int(div_x1), int(top + 32 * scale), int(div_x1), int(bottom - 46 * scale))
        painter.drawLine(int(div_x2), int(top + 32 * scale), int(div_x2), int(bottom - 46 * scale))
        painter.restore()

    # --- 线圈 1 (左后方·方案 A: 跑道形铜色线圈) ---
    c1_x = 90.0 * scale
    c1_y = 100.0 * scale
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    r1_w = 26.0 * scale
    r1_h = 36.0 * scale
    painter.setPen(QPen(QColor("#059669"), max(1.0, 2.2 * scale), Qt.PenStyle.SolidLine))
    rect1 = QRectF(c1_x - r1_w, c1_y - r1_h, r1_w * 2, r1_h * 2)
    painter.drawRoundedRect(rect1, r1_w, r1_w)
    # 内铜圈
    painter.setPen(QPen(QColor("#D97706"), max(1.0, 3.2 * scale)))
    rect1_in = QRectF(c1_x - r1_w * 0.65, c1_y - r1_h * 0.72, r1_w * 1.3, r1_h * 1.44)
    painter.drawRoundedRect(rect1_in, r1_w * 0.65, r1_w * 0.65)
    painter.restore()

    # --- 线圈 2 (右后方·方案 B: 八角形科技线圈) ---
    c2_x = 166.0 * scale
    c2_y = 100.0 * scale
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor("#0284C7"), max(1.0, 2.2 * scale), Qt.PenStyle.SolidLine))
    oct_r = 28.0 * scale
    oct_path = QPainterPath()
    for i in range(8):
        angle_rad = math.radians(22.5 + i * 45.0)
        px = c2_x + oct_r * math.cos(angle_rad)
        py = c2_y + oct_r * math.sin(angle_rad)
        if i == 0:
            oct_path.moveTo(px, py)
        else:
            oct_path.lineTo(px, py)
    oct_path.closeSubpath()
    painter.drawPath(oct_path)
    # 内铜圈
    painter.setPen(QPen(QColor("#F59E0B"), max(1.0, 3.0 * scale)))
    painter.drawEllipse(QPointF(c2_x, c2_y), 16.0 * scale, 16.0 * scale)
    painter.restore()

    # --- 线圈 3 (居中正前方·基准方案 Baseline: 高亮同心铜线圈 + 对比锚点) ---
    c3_x = 128.0 * scale
    c3_y = 126.0 * scale
    painter.save()
    painter.setBrush(Qt.BrushStyle.NoBrush)
    # 实体铜圈
    painter.setPen(QPen(QColor("#EA580C"), max(1.2, 4.2 * scale)))
    painter.drawEllipse(QPointF(c3_x, c3_y), 27.0 * scale, 23.0 * scale)
    painter.setPen(QPen(QColor("#F59E0B"), max(1.0, 3.0 * scale)))
    painter.drawEllipse(QPointF(c3_x, c3_y), 17.0 * scale, 14.5 * scale)

    # 中心翡翠基准亮点 (突出 Baseline 锚定对比概念)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#10B981"))
    painter.drawEllipse(QPointF(c3_x, c3_y), max(1.5, 4.5 * scale), max(1.5, 4.5 * scale))
    painter.restore()

    # 4. 底部工程徽标标签条 (Badge: SCHEMES 格式，翡翠绿渐变)
    if size >= 24:
        tag_w = (right - left) * 0.88
        tag_h = 32.0 * scale
        tag_x = (right + left) / 2.0 - (tag_w / 2.0)
        tag_y = bottom - (44.0 * scale)

        tag_rect = QRectF(tag_x, tag_y, tag_w, tag_h)
        tag_path = QPainterPath()
        tag_path.addRoundedRect(tag_rect, 4.0 * scale, 4.0 * scale)

        # 标签翡翠绿对比渐变 (#059669 -> #047857)
        tag_grad = QLinearGradient(tag_x, tag_y, tag_x + tag_w, tag_y + tag_h)
        tag_grad.setColorAt(0.0, QColor("#059669"))
        tag_grad.setColorAt(1.0, QColor("#047857"))

        painter.fillPath(tag_path, tag_grad)
        painter.setPen(QPen(QColor("#6EE7B7"), max(1.0, 1.5 * scale)))
        painter.drawPath(tag_path)

        # 标签文字: SCHEMES (小图标自适应压缩)
        badge_text = "SCHEMES" if size >= 32 else "SCH"
        font_size = max(5, int(13.0 * scale if size >= 48 else 10.0 * scale))
        font = QFont("Arial", font_size, QFont.Weight.Black)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(0.5, 1.2 * scale))
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

    painter.end()
    return img


def write_ico_file(images: list[QImage], output_ico_path: Path):
    """合成 Windows 多分辨率 ICO 二进制文件"""
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = []
    png_datas = []
    offset = 6 + len(images) * 16

    for img in images:
        from PyQt6.QtCore import QBuffer, QIODevice
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buf, "PNG")
        raw_png = bytes(buf.data())
        buf.close()

        w = img.width() if img.width() < 256 else 0
        h = img.height() if img.height() < 256 else 0
        data_len = len(raw_png)

        entry = struct.pack(
            "<BBBBHHII",
            w, h, 0, 0, 1, 32, data_len, offset
        )
        entries.append(entry)
        png_datas.append(raw_png)
        offset += data_len

    with open(output_ico_path, "wb") as f:
        f.write(header)
        for e in entries:
            f.write(e)
        for d in png_datas:
            f.write(d)


def main():
    root_dir = Path(__file__).resolve().parent.parent
    res_dir = root_dir / "resources"
    res_dir.mkdir(parents=True, exist_ok=True)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for s in sizes:
        img = draw_schemes_file_icon(s)
        images.append(img)
        print(f"Generated schemes file icon resolution: {s}x{s}")

    # 保存 256x256 高清 PNG
    png_path = res_dir / "coil_schemes_icon.png"
    images[-1].save(str(png_path), "PNG")
    print(f"Saved Schemes PNG to: {png_path}")

    # 合成多分辨率 .ico 文件
    ico_path = res_dir / "coil_schemes_icon.ico"
    write_ico_file(images, ico_path)
    print(f"Saved Schemes Multi-Res ICO to: {ico_path} (size: {ico_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
