"""
验证单实例 IPC 静默转发与外部算例覆盖确认机制
"""
import sys
import os
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from src.gui.main_window import MainWindow
from src.core.ipc_manager import SingleInstanceIPCServer, send_args_to_running_instance

print("=== 1. 启动主窗口与 IPC 服务端 ===")
win = MainWindow()
win.show()

ipc_server = SingleInstanceIPCServer(win)

# 记录接收到的信号
received_events = []

ipc_server.file_import_requested.connect(lambda p: received_events.append(("OPEN", p)))
ipc_server.activate_requested.connect(lambda: received_events.append(("ACTIVATE", None)))

# 刷新 Qt 事件循环使服务就绪
app.processEvents()

print("\n=== 2. 模拟次进程双击打开 .ansvcoil 算例文件 ===")
test_file = Path("sample_external.ansvcoil").resolve()
with open(test_file, "w", encoding="utf-8") as f:
    f.write('{"inputs": {}}')

import subprocess

try:
    # 使用独立的外部 Python 子进程模拟真实的次进程启动
    sub_cmd = [
        sys.executable, "-c",
        f"from PyQt6.QtWidgets import QApplication; import sys, os; app = QApplication(sys.argv); "
        f"from pathlib import Path; sys.path.insert(0, str(Path('.').resolve())); "
        f"from src.core.ipc_manager import send_args_to_running_instance; "
        f"ok = send_args_to_running_instance(r'{test_file}'); "
        f"print('Subprocess send result:', ok); sys.exit(0 if ok else 1)"
    ]
    proc = subprocess.Popen(sub_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # 主进程持续刷新 Qt 事件循环响应 IPC 报文，避免阻塞
    start_t = time.time()
    while proc.poll() is None and (time.time() - start_t < 5):
        app.processEvents()
        time.sleep(0.02)
    
    out, err = proc.communicate()
    print("次进程输出:", out.strip())
    assert proc.returncode == 0, f"次进程应当成功返回 0: {err}"

    # 主进程等待并消费剩余事件
    for _ in range(20):
        app.processEvents()
        time.sleep(0.02)
        if received_events:
            break

    print("主工作台接收到的事件:", received_events)
    assert len(received_events) >= 1, "主工作台应当接收到外部事件"
    event_type, path_payload = received_events[0]
    assert event_type == "OPEN", "事件类型应当为 OPEN"
    assert Path(path_payload).resolve() == test_file, f"传递的文件路径应一致: {path_payload}"
    print("✅ 外部算例文件路径无缝传递测试 PASS！")

    print("\n=== 3. 模拟次进程单纯重复双击快捷方式 (无文件参数) ===")
    received_events.clear()
    sub_activate_cmd = [
        sys.executable, "-c",
        f"from PyQt6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); "
        f"from pathlib import Path; sys.path.insert(0, str(Path('.').resolve())); "
        f"from src.core.ipc_manager import send_args_to_running_instance; "
        f"ok = send_args_to_running_instance(''); "
        f"print('Subprocess activate result:', ok); sys.exit(0 if ok else 1)"
    ]
    proc2 = subprocess.Popen(sub_activate_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    start_t2 = time.time()
    while proc2.poll() is None and (time.time() - start_t2 < 5):
        app.processEvents()
        time.sleep(0.02)
    
    out2, err2 = proc2.communicate()
    print("次进程输出:", out2.strip())
    assert proc2.returncode == 0, f"次进程激活应成功返回 0: {err2}"

    for _ in range(20):
        app.processEvents()
        time.sleep(0.02)
        if received_events:
            break

    print("主工作台接收到的事件:", received_events)
    assert len(received_events) >= 1, "主工作台应当接收到激活事件"
    assert received_events[0][0] == "ACTIVATE", "事件类型应当为 ACTIVATE"
    print("✅ 重复双击静默唤醒测试 PASS！")

finally:
    if test_file.exists():
        test_file.unlink()
    ipc_server.close_server()
    win.close()

print("\n🎉 单实例 IPC 与外部算例无缝路由端到端测试 100% 全部通过！")
