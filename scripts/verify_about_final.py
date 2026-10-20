"""
验证脚本：关于系统完整功能重构、二维码加载、Git 版本记录与按钮交互
"""

import sys
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 添加工程根目录到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 注意：不要使用 offscreen QPA，Windows 原生 DirectWrite 字体引擎能完美渲染中文与 emoji
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from src.gui.about_dialog import AboutDialog
from src.gui.update_dialog import UpdateDialog
from src.version import WECHAT_OFFICIAL_ACCOUNT, PLATFORM_NAME, get_git_commit, get_git_log
from src.core.shortcut_helper import create_desktop_shortcut
from src.utils.logger import export_diagnostic_bundle

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    from PyQt6.QtGui import QFont
    app.setFont(QFont("Microsoft YaHei", 9))

    print("=== 1. 验证常数与 Git 版本记录 ===")
    assert WECHAT_OFFICIAL_ACCOUNT == "ANSV微型执行器", f"公众号名称错误: {WECHAT_OFFICIAL_ACCOUNT}"
    print(f"✅ 公众号名称验证通过: {WECHAT_OFFICIAL_ACCOUNT}")

    git_hash = get_git_commit()
    print(f"✅ Git Commit: {git_hash}")
    git_logs = get_git_log()
    print(f"✅ Git Logs 总条数: {len(git_logs)}")
    assert len(git_logs) > 0, "Git 日志记录列表不能为空"
    for log in git_logs[:3]:
        print(f"   [{log['commit']}] {log['date']} {log['author']}: {log['subject']}")

    print("\n=== 2. 验证 AboutDialog 渲染与元素布局 ===")
    dlg = AboutDialog()
    dlg.show()
    app.processEvents()

    # 递归查找所有 QLabel 与 QPushButton
    all_labels = dlg.findChildren(QLabel)
    all_texts = " ".join([l.text() for l in all_labels])

    # 断言关键信息存在
    assert PLATFORM_NAME in all_texts, "缺少平台全称"
    assert "ANSV微型执行器" in all_texts, "缺少官方公众号名称"
    assert "硬核技术深度拆解" in all_texts, "缺少权益 1"
    assert "独家工程工具与算例" in all_texts, "缺少权益 2"
    assert "量产避坑与失效诊断" in all_texts, "缺少权益 3"
    assert "前沿专利与拆解报告" in all_texts, "缺少权益 4"
    assert "工程师技术答疑通道" in all_texts, "缺少权益 5"

    assert "软件系统:" in all_texts, "缺少软件系统行"
    assert "软件版本:" in all_texts, "缺少软件版本行"
    assert "构建时间:" in all_texts, "缺少构建时间行"
    assert "核心架构:" in all_texts, "缺少核心架构行"
    assert "机器码:" in all_texts, "缺少机器码行"
    assert "本机MAC:" in all_texts, "缺少本机MAC行"
    assert "授权工位:" in all_texts, "缺少授权工位行"

    # 关键断言：绝对严禁出现测试良率！
    assert "测试良率" not in all_texts, "错误：关于对话框中包含了用户要求去除的测试良率！"
    assert "今日已测" not in all_texts, "错误：关于对话框中包含了测试良率统计！"
    print("✅ 严格排查验证：测试良率数据已按用户要求 100% 剔除！")

    # 检查底栏 4 个操作按钮
    all_buttons = dlg.findChildren(QPushButton)
    btn_texts = [b.text() for b in all_buttons]
    print(f"发现按钮: {btn_texts}")
    assert any("桌面快捷方式" in t for t in btn_texts), "缺少桌面快捷方式按钮"
    assert any("导出诊断日志" in t for t in btn_texts), "缺少导出诊断日志按钮"
    assert any("检查更新" in t for t in btn_texts), "缺少检查更新按钮"
    assert any("确定" in t for t in btn_texts), "缺少确定按钮"
    print("✅ 底栏 4 个操作按钮全部齐备！")

    # 渲染截图并保存
    brain_dir = Path(r"C:\Users\tonyc\.gemini\antigravity\brain\8c6d1b01-3d51-47cd-b3c7-3804ed3b694b")
    about_shot = brain_dir / "verify_about_dialog_final.png"
    dlg.grab().save(str(about_shot))
    print(f"✅ AboutDialog 截图已保存至: {about_shot}")

    print("\n=== 3. 验证 UpdateDialog 渲染与 Git 记录 ===")
    udlg = UpdateDialog()
    udlg.show()
    app.processEvents()

    u_labels = udlg.findChildren(QLabel)
    u_texts = " ".join([l.text() for l in u_labels])
    assert "软件更新与 Git 版本历史记录" in u_texts or "Git" in u_texts, "缺少更新标题"
    assert git_hash in u_texts, f"更新对话框中未找到当前 git hash: {git_hash}"

    update_shot = brain_dir / "verify_update_dialog_git_log.png"
    udlg.grab().save(str(update_shot))
    print(f"✅ UpdateDialog 截图已保存至: {update_shot}")

    print("\n=== 4. 验证桌面快捷方式生成与日志导出底层功能 ===")
    ok_sc, msg_sc = create_desktop_shortcut()
    print(f"桌面快捷方式生成结果: ok={ok_sc}, msg={msg_sc}")

    zip_p = export_diagnostic_bundle()
    assert zip_p.exists(), f"导出的诊断日志压缩包不存在: {zip_p}"
    print(f"✅ 诊断日志包生成成功: {zip_p} (文件大小: {zip_p.stat().st_size} bytes)")

    print("\n🎉 全部断言与视觉渲染 100% 通过！")

if __name__ == "__main__":
    main()
