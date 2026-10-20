"""
生成 ANSV Coil-Architect Pro 专属工程算例文件图标 (.ansvcoil)
与主程序图标明确区分：
- 主程序图标: 科技深色底座 + 发光电磁双环 (代表工作站应用本体)
- 算例文件图标: 高质感工业折角文档纸张 + 黄金电磁线圈印章 + 底部专属 COIL 徽标 (代表物理仿真数据算例)
包含 7 层全金字塔自适应分辨率: 16, 24, 32, 48, 64, 128, 256
"""

import sys
import os
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


def draw_project_file_icon(size: int) -> QImage:
    """绘制指定尺寸的专属工程算例文件图标"""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale = size / 256.0

    # 1. 经典工程文档几何轮廓 (带右上角 45° 优雅折角)
    # 尺寸参数 (基于 256x256 基准)
    left = 32.0 * scale
    top = 18.0 * scale
    right = 224.0 * scale
    bottom = 238.0 * scale
    corner = 52.0 * scale  # 折角大小
    radius = 10.0 * scale  # 纸张四角微圆角

    # 构建文档主路径 (不包含右上折角部分)
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

    # 纸张投影背影 (微柔和外阴影)
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

    # 纸张渐变底衬 (高质感银白工程图纸，略带天蓝物理科技感)
    paper_grad = QLinearGradient(0, top, 0, bottom)
    paper_grad.setColorAt(0.0, QColor("#FFFFFF"))
    paper_grad.setColorAt(0.7, QColor("#F8FAFC"))
    paper_grad.setColorAt(1.0, QColor("#E2E8F0"))

    painter.setPen(QPen(QColor("#94A3B8"), max(1.0, 3.0 * scale)))
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
    flap_grad.setColorAt(0.0, QColor("#CBD5E1"))
    flap_grad.setColorAt(0.5, QColor("#E2E8F0"))
    flap_grad.setColorAt(1.0, QColor("#FFFFFF"))

    painter.setPen(QPen(QColor("#94A3B8"), max(1.0, 2.5 * scale)))
    painter.setBrush(flap_grad)
    painter.drawPath(flap_path)

    # 3. 核心区域：绘制黄金电磁微型线圈印章 (八角形与双跑道环)
    center_x = 128.0 * scale
    center_y = 115.0 * scale

    # 外层八角形电磁引导虚线
    if size >= 32:
        painter.save()
        painter.setPen(QPen(QColor("#0284C7"), max(1.0, 2.2 * scale), Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        oct_r = 46.0 * scale
        oct_path = QPainterPath()
        import math
        for i in range(8):
            angle_rad = math.radians(22.5 + i * 45.0)
            px = center_x + oct_r * math.cos(angle_rad)
            py = center_y + oct_r * math.sin(angle_rad)
            if i == 0:
                oct_path.moveTo(px, py)
            else:
                oct_path.lineTo(px, py)
        oct_path.closeSubpath()
        painter.drawPath(oct_path)
        painter.restore()

    # 核心铜线圈同心环 (金铜色漆包线微观质感)
    ring_radii = [34.0 * scale, 24.0 * scale, 14.0 * scale]
    copper_colors = ["#D97706", "#F59E0B", "#B45309"]
    for idx, r in enumerate(ring_radii):
        pen_w = max(1.2, 4.5 * scale if idx != 1 else 3.5 * scale)
        painter.setPen(QPen(QColor(copper_colors[idx % len(copper_colors)]), pen_w))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(center_x, center_y), r, r * 0.88)

    # 中心高能物理核心亮点
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#0284C7"))
    painter.drawEllipse(QPointF(center_x, center_y), max(1.5, 4.5 * scale), max(1.5, 4.5 * scale))

    # 4. 底部工程徽标标签条 (Badge: COIL 格式)
    if size >= 24:
        tag_w = (right - left) * 0.76
        tag_h = 32.0 * scale
        tag_x = center_x - (tag_w / 2.0)
        tag_y = bottom - (44.0 * scale)

        tag_rect = QRectF(tag_x, tag_y, tag_w, tag_h)
        tag_path = QPainterPath()
        tag_path.addRoundedRect(tag_rect, 4.0 * scale, 4.0 * scale)

        # 标签深蓝科技渐变
        tag_grad = QLinearGradient(tag_x, tag_y, tag_x + tag_w, tag_y + tag_h)
        tag_grad.setColorAt(0.0, QColor("#0284C7"))
        tag_grad.setColorAt(1.0, QColor("#0369A1"))

        painter.fillPath(tag_path, tag_grad)
        painter.setPen(QPen(QColor("#38BDF8"), max(1.0, 1.5 * scale)))
        painter.drawPath(tag_path)

        # 标签文字
        font_size = max(6, int(15.0 * scale))
        font = QFont("Arial", font_size, QFont.Weight.Black)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, max(0.5, 2.0 * scale))
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, "COIL")

    # 5. 顶部图纸微网格装饰线 (仅在大图标展示)
    if size >= 64:
        painter.setPen(QPen(QColor("#CBD5E1"), 1.0 * scale, Qt.PenStyle.DotLine))
        painter.drawLine(int(left + 14 * scale), int(top + 28 * scale), int(right - corner - 8 * scale), int(top + 28 * scale))
        painter.drawLine(int(left + 14 * scale), int(top + 40 * scale), int(right - corner - 18 * scale), int(top + 40 * scale))

    painter.end()
    return img


def write_ico_file(images: list[QImage], output_ico_path: Path):
    """将多尺寸 QImage 合成为合法的 Windows 多分辨率 .ico 二进制文件"""
    # ICO 头部: 0 (保留), 1 (ICO 类型), 数量
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = []
    png_datas = []

    offset = 6 + len(images) * 16

    for img in images:
        import io
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
        img = draw_project_file_icon(s)
        images.append(img)
        print(f"Generated project file icon resolution: {s}x{s}")

    # 保存 256x256 高清 PNG
    png_path = res_dir / "coil_project_icon.png"
    images[-1].save(str(png_path), "PNG")
    print(f"Saved PNG to: {png_path}")

    # 合成包含全分辨率的 .ico 文件
    ico_path = res_dir / "coil_project_icon.ico"
    write_ico_file(images, ico_path)
    print(f"Saved Multi-Res ICO to: {ico_path} (size: {ico_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
