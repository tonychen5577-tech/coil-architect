"""
=============================================================================
Module: src.core.ipc_manager
Description: Coil-Architect Pro 进程间通信 (IPC) 与单实例算例自动路由管理器
基于 Windows 命名管道 (Qt QLocalServer / QLocalSocket)：
1. 二次启动时静默将待打开的算例路径发送给已在运行的主工作台，彻底消灭双开冲突警告；
2. 主工作台接收到外部算例请求后，前台唤醒并弹出“是否导入数据并覆盖现有数据”的确认弹窗。
=============================================================================
"""

import sys
import os
import ctypes
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from src.utils.logger import get_logger

logger = get_logger("IPCManager")

IPC_SERVER_NAME = "CoilArchitect_SingleInstance_IPC_2026"


def send_args_to_running_instance(filepath: str = "") -> bool:
    """
    次进程调用：检测是否有已运行的主工作台，并尝试将入参静默投递给主工作台
    :param filepath: 外部请求打开的算例文件路径 (若无则仅唤醒前台)
    :return: True 表示已成功投递给主工作台，当前次进程应静默退出；
             False 表示无运行中的主工作台，当前进程应作为主实例启动。
    """
    try:
        socket = QLocalSocket()
        socket.connectToServer(IPC_SERVER_NAME)
        # 等待 500ms 连接已有服务器
        if socket.waitForConnected(500):
            target_path = os.path.abspath(filepath) if filepath and os.path.exists(filepath) else ""
            msg = f"OPEN:{target_path}" if target_path else "ACTIVATE"

            payload = msg.encode("utf-8")
            socket.write(payload)
            socket.flush()
            socket.waitForBytesWritten(1000)
            # 等待服务端接收完毕并安全断开
            socket.waitForDisconnected(1000)
            logger.info(f"成功将启动指令 [{msg}] 投递给已在运行的主工作台。")
            return True
        return False
    except Exception as e:
        logger.debug(f"连接已有实例 IPC 通道失败 (可能尚未启动): {e}")
        return False


class SingleInstanceIPCServer(QObject):
    """
    主进程常驻 IPC 服务端：
    监听来自外部双击文件或快捷方式二次调用的请求
    """
    file_import_requested = pyqtSignal(str)  # 传递待载入的文件绝对路径
    activate_requested = pyqtSignal()        # 唤醒窗口置顶信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._clients = []
        self.server = QLocalServer(self)
        # 清理异常崩溃可能残留的废弃管道
        QLocalServer.removeServer(IPC_SERVER_NAME)

        self.server.newConnection.connect(self._on_new_connection)
        ok = self.server.listen(IPC_SERVER_NAME)
        if ok:
            logger.info(f"单实例 IPC 服务端已成功启动监听: {IPC_SERVER_NAME}")
        else:
            logger.warning(f"单实例 IPC 服务端监听失败: {self.server.errorString()}")

    def _on_new_connection(self):
        """响应次进程发送的报文"""
        client = self.server.nextPendingConnection()
        if not client:
            return

        self._clients.append(client)

        def handle_read():
            raw_data = client.readAll().data()
            if not raw_data:
                return
            msg = raw_data.decode("utf-8", errors="ignore").strip()
            logger.info(f"IPC 服务端接收到外部指令: {msg}")

            if msg.startswith("OPEN:"):
                fpath = msg[5:].strip()
                if fpath and os.path.exists(fpath):
                    self.file_import_requested.emit(fpath)
                else:
                    self.activate_requested.emit()
            elif msg == "ACTIVATE":
                self.activate_requested.emit()
            else:
                self.activate_requested.emit()

            if client in self._clients:
                self._clients.remove(client)
            client.disconnectFromServer()
            client.deleteLater()

        client.readyRead.connect(handle_read)
        client.disconnected.connect(lambda: self._clients.remove(client) if client in self._clients else None)

        if client.bytesAvailable() > 0:
            handle_read()

    def close_server(self):
        """安全关闭服务端"""
        if self.server and self.server.isListening():
            self.server.close()
            QLocalServer.removeServer(IPC_SERVER_NAME)
