"""
=============================================================================
Module: src.version
Description: Coil-Architect Pro 软件版本、构建指纹与发布配置
统一管理软件全量版本标识、语义化版本比对规则与研发代码编辑追溯指纹
-----------------------------------------------------------------------------
REVISION HISTORY (软件编辑留痕):
- 2026-10-14 [Yaming] v1.1.0: 架构与外观体系全面对齐 FFT 分析软件 (Gear-NVH / Gear-Acoustics)：
                             1) 引入 src.version 集中版本指纹与代码编辑追溯机制；
                             2) 引入 src.utils.logger 全局安全滚动日志 (5MB) 与 Windows GBK 安全输出；
                             3) 引入 src.core.single_instance 内核级 Windows Named Mutex 单实例防双开；
                             4) 引入 src.gui.icon_helper 多分辨率图标管理与 Win32 HWND 强注入；
                             5) 引入 src.gui.splash_screen 16:9 SolidWorks 纯白工业测控启动闪屏；
                             6) 强化 styles.py 的 apply_light_theme (Fusion + QPalette) 彻底免疫 Windows 深色模式黑底污染；
                             7) 全面收敛 MainWindow、AboutDialog、ActivationDialog 版本号与品牌定义，更新 APP_BUILD 为 20261014_B1
=============================================================================
"""

APP_NAME = "Coil-Architect Pro"
APP_TITLE = "Coil-Architect Pro | 电磁线圈多物理场仿真工作站"
PLATFORM_NAME = "ANSV 微型执行器与精密传动仿真验证平台"
PLATFORM_NAME_EN = "Actuator Numerical Simulation & Validation"
PLATFORM_FULL_TITLE = "ANSV 微型执行器与精密传动仿真验证平台 (Actuator Numerical Simulation & Validation)"
WECHAT_OFFICIAL_ACCOUNT = "ANSV微型执行器与精密传动"
APP_VERSION = "v1.1.0"
APP_BUILD = "20261014_B1"
APP_DATE = "2026-10-14"
APP_AUTHOR = "ANSV 传动工程与微型执行器实验室"
OFFICIAL_URL = "https://ansv.net"
COPYRIGHT_TEXT = "Copyright © 2026 ANSV Transmissions & Micro-Actuators Lab. All Rights Reserved."
CORE_ENGINE_AUTHOR = "Yaming.Chen"
