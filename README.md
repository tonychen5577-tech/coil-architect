<div align="center">

# ⚡ ANSV Coil-Architect Pro | 电磁线圈多物理场仿真工作站
### Actuator Numerical Simulation & Validation | Industrial Micro-Coil Topology & Multiphysics CAE Platform (v1.1.0)

[![Release](https://img.shields.io/badge/Release-v1.1.0-0284C7?style=flat-square&logo=github)](https://github.com/tonychen5577-tech/coil-architect/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(64--bit)-0284C7?style=flat-square&logo=windows)](https://github.com/tonychen5577-tech/coil-architect)
[![License](https://img.shields.io/badge/License-Commercial%20%2F%20Free%20Evaluation-059669?style=flat-square)](https://github.com/tonychen5577-tech/coil-architect)
[![Architecture](https://img.shields.io/badge/Core-Cython%20x86__64%20Native-334155?style=flat-square)](https://github.com/tonychen5577-tech/coil-architect)
[![Official Site](https://img.shields.io/badge/Official%20Site-ansv.net-38BDF8?style=flat-square&logo=safari)](https://ansv.net)

<p align="center">
  <b>专为手机摄像头模组 (VCM)、微型执行器 (LRA/触觉马达)、精密电磁阀及传动系统量身打造的高精度电磁线圈多物理场仿真与 DFM 工程化工作站</b>
</p>

[📥 软件下载与部署](#-软件下载与部署) • [✨ 核心功能亮点](#-核心功能亮点) • [📐 八角形异形线圈求解机理](#-八角形异形线圈多物理场反推机理) • [🛡️ DFM 工艺红线与 ISO 129 标注](#-磁钢气隙装配-dfm-工艺红线与-iso-129-标注) • [📊 多方案微调对比抽屉](#-多方案微调数据对比抽屉与-excel-自适应导出) • [🔑 商业授权与订阅模式](#-软件授权与订阅模式) • [📬 专属联系通道](#-技术支持与专属联系通道)

</div>

---

## 📖 系统简介 (System Overview)

**Coil-Architect Pro** 是 **ANSV 微型执行器与精密传动仿真验证平台 (Actuator Numerical Simulation & Validation)** 旗下的核心电磁线圈求解器工作站。

在高端智能手机潜望镜头、微型音圈电机 (VCM)、线性振动马达 (LRA) 以及精密医疗执行器设计中，线圈通常被严苛限制在毫米乃至微米级的极窄装配腔体内。传统线圈排布过度依赖工程师的**“经验查表与手工盲目试凑”**，面临**对角干涉严重、铜线拉伸减径偏差大、真实漆膜厚度失真、常温/工作温升电阻超标、打样试产报废率高**等行业痛点。

Coil-Architect Pro 深度整合了**异形微型线圈几何拓扑解析、张力拉伸减径补偿、微米级自粘漆包绝缘膜精算、电-磁-热多物理场耦合与磁钢气隙 DFM 制造干涉预警**：

输入装配腔体约束与目标电阻，软件可在秒级内自动反演倒推出最佳绕线层数、圈数排布、对边对角内外径、成型厚度与真实热态阻值，并一键输出符合 **ISO 129** 国际标准的工程截面投影图与自适应排版评审报表，为微型执行器的敏捷研发与量产直通率保驾护航。

<p align="center">
  <img src="docs/images/main_ui_preview.png" alt="Coil-Architect Pro 主工作区全景" width="95%" />
  <br>
  <em>图 1：ANSV Coil-Architect Pro 工作站主界面 —— 微型执行器多物理场参数解算与排线截面实时渲染</em>
</p>

---

## ✨ 核心功能亮点 (Core Features)

### 1. 业内公认难算的“八角形异形线圈”参数极速反推
- **专为旗舰手机镜头马达与微型执行器打造**：完整支持**八角形异形线圈、跑道形线圈、矩形圆角线圈与经典圆环线圈**；
- **智能目标倒推引擎**：只需输入对边/对角装配空间、拐角内圆角半径与目标电阻容差（如 $19.5 \pm 3\,\Omega$），系统毫秒级反推最佳导体线径、漆包外径、层数（Layers）与每层匝数（Turns）。

### 2. 张力拉伸减径与微米级真实自粘漆膜拓扑解算
- **真实工况拉伸减径补偿**：打破传统恒定线径假设，引入拉伸系数模型（$k_{\text{stretch}} = 0.99 \sim 0.97$），精准预测微米级铜芯变细量；
- **漆膜层厚度精确计算**：自动计入最薄 $0.008\,\text{mm}$ 级绝缘漆层与自粘胶层厚度，杜绝打样后线圈外径胀大导致装不进马达壳体的致命失误；
- **温度特性全温区修正**：精准解算 $20^\circ\text{C}$ 冷态电阻与 $70^\circ\text{C} \sim 120^\circ\text{C}$ 工作温升极限电阻。

### 3. 磁钢装配气隙 DFM 制造工艺红线主动预警
- **三维气隙动态干涉感知**：实时解算线圈与外围多极磁钢组的径向间隙（Air Gap）与装配公差；
- **DFM 工艺安全红线主动诊断**：气隙 $< 0.15\,\text{mm}$ 触发黄色预警，$< 0.10\,\text{mm}$ 强制红色高危阻断，杜绝试产跌落划线破膜短路；
- **ISO 129 截面标注**：自动绘制投影尺寸界线、规范实心闭合箭头与 ISO 5459 `[ A ]` 形位公差基准特征符号。

### 4. 底部微调数据对比折叠抽屉与 Excel 自适应报表
- **方案固化与横向比对**：支持工程师将微调中的关键参数【📌 固化为方案】，多方案同屏纵向/横向对比，滚轮流畅滚动；
- **Excel 智能自适应列宽导出**：依据 ISO 129 规范工程制图代号输出，列宽动态按中英文字符加权自适应缓冲，打开报表无需手动拖拽调整列宽；
- **时间戳溯源防重名**：所有算例存档、对比表及工程评审报告自动附加 `_YYYYMMDD_HHMMSS`。

---

## 📐 八角形异形线圈多物理场反推机理

在微型执行器（如 50MP/200MP 手机潜望摄像头马达、小型触觉致动器）中，八角形线圈因空间利用率极高而被广泛采用，但其内角 $135^\circ$ 的几何嵌套推演极为复杂。

```
        /───────────────\
       /                 \
      |   八角形微型线圈    |  <--- 对边内外径 (Opposite Flat)
      |   (8-Sided Coil)  |
       \                 /   <--- 对角内外径 (Corner Diagonal)
        \───────────────/
```

### 1. 对边内径与对角内径几何约束方程
设对边内径为 $W_{\text{opp}}$，拐角过渡圆角为 $R$，对角内径 $W_{\text{diag}}$ 满足严格几何解析约束：
$$W_{\text{diag}} = \frac{W_{\text{opp}}}{\cos(22.5^\circ)} - 2R \left(\frac{1}{\cos(22.5^\circ)} - 1\right)$$
Coil-Architect Pro 通过闭式解析解直接消除传统数值离散求交的累积误差，确保内八角与外八角在任意绕线层数下保持完美的微米级同心与等间距。

### 2. 铜线拉伸减径修正方程
高速绕线机张力机构对极细铜线（裸铜 $\le 0.05\,\text{mm}$）产生不可忽视的塑性微拉伸：
$$d_{\text{eff}} = d_{\text{bare}} \times \sqrt{k_{\text{stretch}}}$$
电阻计算采用拉细后的等效导体截面积 $A_{\text{eff}} = \frac{\pi d_{\text{eff}}^2}{4}$，使最终成型电阻计算吻合度提升至 **$99.2\%$** 以上。

---

## 🛡️ 磁钢气隙装配 DFM 工艺红线与 ISO 129 标注

<p align="center">
  <img src="docs/images/verify_iso_section_view.png" alt="ISO 129 标准线圈工程制图截面图" width="95%" />
  <br>
  <em>图 2：符合 ISO 129 标准的 2D 截面投影标注图（含基准特征符号 [ A ] 与全尺寸链公差）</em>
</p>

- **内径/外径尺寸界线**：严格遵循投影尺寸界线垂直引出原则，尺寸数值与代号居中水平标注；
- **磁钢装配气隙预警**：与磁钢的最近安全气隙直接关联，提供红/黄/绿工业三态实时安全指示灯。

---

## 💻 工业级关于系统与无感更新体系

软件采用 **16:9 SolidWorks 纯白工业测控风格**，支持 Git 版本构建留痕、系统诊断包一键打包导出与多通道直连：

<p align="center">
  <img src="docs/images/about_channel_1_official.png" alt="关于系统对话框全景" width="90%" />
  <br>
  <em>图 3：ANSV 仿真平台「关于系统」对话框 —— 集成硬件特征码、Git 源码指纹、一键诊断日志打包与多通道联系卡片</em>
</p>

---

## 📥 软件下载与部署 (Download & Deployment)

本软件为**纯绿色便携免安装设计**，无需配置任何 Python 环境或第三方依赖库，解压即可运行：

1. 前往 GitHub 官方 Releases 下载最新加固绿色包：
   👉 **[点击前往 Releases 下载页面](https://github.com/tonychen5577-tech/coil-architect/releases)**
2. 下载并解压 `ANSV_Coil_Architect_Pro_v1.1.0_Release.zip` 至常用工作目录（如 `D:\Coil_Architect_Pro` 或电脑桌面）；
3. 双击 `Coil-Architect-Pro.exe` 即可毫秒级启动工作站。

> 💡 **系统运行环境要求**：
> - **操作系统**：Windows 10 / Windows 11 (64-bit)
> - **硬件推荐**：Intel Core i3 或更高 / 4GB 内存 / 300MB 可用硬盘空间
> - **显示分辨率**：推荐 $1920 \times 1080$ 或更高高分屏（支持 Windows 125% / 150% 高 DPI 自适应）

---

## 🔑 软件授权与订阅模式 (Licensing)

系统采用纯正的**硬件特征码 (HMAC-SHA256) 一机一码离线验证看门狗机制**，充分保障客户的数据安全与核心工艺资产，**工位机全程无需连接外网即可离线安全运行**。

```
步骤 1: 下载解压并双击启动主程序 Coil-Architect-Pro.exe
   │
   ▼
步骤 2: 首次运行自动享受 7 天全功能免激活试用；
   │
   ▼
步骤 3: 需商业授权或长期订阅时，在软件中点击【复制机器码】(如: COIL-609D-64D4-5D11-35E2)；
   │
   ▼
步骤 4: 通过下方微信或 WhatsApp 专属联系通道获取激活码，粘贴即可秒级激活！
```

### 商业订阅模式：

| 授权方案 | 适用周期 | 核心定位与适用场景 | 服务支持 |
| :--- | :--- | :--- | :--- |
| 🟢 **项目试用版** | 7 ~ 30 天 | 适用于短期打样评估、特定镜头马达项目竞标与方案验证 | 快速技术答疑 |
| 🟢 **季度订阅版** | 3 个月 (90天) | 适用于 EVT/DVT/PVT 试产爬坡期、季节性订单专项攻关 | 在线工程支持 |
| 🟢 **年度商业版** | 1 年 (365天) | 适用于执行器研发中心、马达模组设计企业常态化算例研发 | 免费小版本升级与故障排查 |
| 🟢 **企业级买断** | 永久有效 | 深度嵌入企业核心生产工位、模具机台，一次性永久授权 | 专属深度技术研讨通道 |

---

## 📬 技术支持与专属联系通道 (Contact Us)

如果您在使用 **Coil-Architect Pro** 过程中有任何技术疑问、算例定制需求或商业授权咨询，欢迎通过以下通道与软件研发团队直接取得联系：

> 🛡️ **隐私保护承诺**：为防止骚扰与泄露个人手机号，所有沟通均采用二维码与专属技术账号直达。

<div align="center">

| 1. 📢 官方微信公众号 | 2. 💬 工程师专属微信咨询 | 3. 🌐 WhatsApp (International) |
| :---: | :---: | :---: |
| <img src="docs/images/qr_official_account.jpg" width="160" alt="官方公众号" /> | <img src="docs/images/qr_wechat_personal.png" width="160" alt="工程师微信" /> | <img src="docs/images/qr_whatsapp.png" width="160" alt="WhatsApp" /> |
| **公众号**：`ANSV微型执行器` | **微信号**：`ansv-net` | **WhatsApp**：`ansv_net` |
| 硬核多物理场拆解与一线实战复盘 | 一对一技术支持、算例定制与工程咨询 | Global direct technical support for overseas & APAC partners |

</div>

- **官方网站**：[https://ansv.net](https://ansv.net)
- **GitHub 官方发布仓库**：[tonychen5577-tech/coil-architect](https://github.com/tonychen5577-tech/coil-architect)
- **技术咨询邮箱**：`contact@ansv.net`

---

<div align="center">
  <sub>Copyright © 2026 ANSV Transmissions & Micro-Actuators Lab & ansv.net. All rights reserved. | 工业测控 · 仿真验证 · 追求卓越</sub>
</div>
