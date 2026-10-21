#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
Script: tools/generate_html_manual.py
Description: 将 GitHub 官方 README.md 转换为独立离线高保真 HTML 格式使用说明书
特性：
1. [零外部依赖离线阅读] 自动将 docs/images 中的高清截图、拓扑图与二维码转为 Base64 内嵌 Data URI；
2. [工业级响应式排版] 深度对齐 ANSV 工业蓝与纯净测控灰现代设计系统，适配 4K 宽屏至移动端；
3. [打印与归档友好] 内置 @media print 打印机样式，支持工程师在浏览器中直接「Ctrl+P」无损另存为 PDF 说明书；
4. [双向自动同步] 可被 build_exe.py 打包流水线直接调用，自动打包至绿色全量安装包与增量升级包根目录。
=============================================================================
"""

import os
import sys
import re
import base64
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent

try:
    import markdown
except ImportError:
    print("[Error] 请先安装 markdown 库: pip install markdown")
    sys.exit(1)


def build_html_manual(
    md_path: Path = ROOT_DIR / "README.md",
    output_html_paths: list = None
) -> Path:
    if not output_html_paths:
        output_html_paths = [
            ROOT_DIR / "docs" / "Coil-Architect-Pro_使用说明书.html",
            ROOT_DIR / "dist" / "Coil-Architect-Pro" / "Coil-Architect-Pro_使用说明书.html",
            ROOT_DIR / "dist" / "Coil-Architect-Pro" / "README.html",
        ]

    if not md_path.exists():
        raise FileNotFoundError(f"未找到源说明书文件: {md_path}")

    print(f"[Manual] 正在读取说明书源文件: {md_path} ...")
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # 1. 内嵌 Base64 图片转换
    print("[Manual] 正在将本地图库与拓扑架构图内嵌为 Base64 数据流...")
    embedded_count = 0

    def _replace_image_path(match):
        nonlocal embedded_count
        raw_tag = match.group(0)
        img_rel_path = match.group(1).split("?")[0].split("#")[0]
        img_abs_path = (ROOT_DIR / img_rel_path).resolve()

        if img_abs_path.exists() and img_abs_path.is_file():
            ext = img_abs_path.suffix.lower().lstrip(".")
            mime = "image/jpeg" if ext in ["jpg", "jpeg"] else "image/png"
            with open(img_abs_path, "rb") as img_file:
                b64_str = base64.b64encode(img_file.read()).decode("utf-8")
            data_uri = f"data:{mime};base64,{b64_str}"
            embedded_count += 1
            return raw_tag.replace(match.group(1), data_uri)
        return raw_tag

    # 匹配 <img src="...">
    md_content = re.sub(
        r'<img[^>]+src=[\x22\x27](docs/images/[^\x22\x27]+)[\x22\x27]',
        _replace_image_path,
        md_content
    )
    # 匹配 markdown ![alt](path)
    md_content = re.sub(
        r'!\[.*?\]\((docs/images/.*?)\)',
        _replace_image_path,
        md_content
    )
    print(f"  ✓ 成功完成 {embedded_count} 张高清图片/架构图的零依赖数据内嵌！")

    # 2. 转换简易数学公式符号为优雅样式
    # 将 $formula$ 转换为 <span class="math-tex">formula</span>
    def _math_sub(m):
        raw = m.group(1)
        # 简单美化常见公式符号
        pretty = raw.replace(r"\times", " × ").replace(r"\cdot", " · ")
        pretty = pretty.replace(r"\text{in}", "in").replace(r"\text{corner}", "corner")
        return f'<span class="math-tex">{pretty}</span>'

    md_content = re.sub(r'\$([^\$\n]+?)\$', _math_sub, md_content)

    # 3. 使用 Markdown 扩展引擎解析核心语法
    print("[Manual] 正在编译 Markdown 为标准化语义 HTML5 节点...")
    extensions = [
        "extra",
        "tables",
        "fenced_code",
        "codehilite",
        "toc",
        "nl2br",
        "sane_lists"
    ]
    html_body = markdown.markdown(md_content, extensions=extensions)

    # 4. 组装工业级独立发布 HTML5 模板
    html_document = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ANSV Coil-Architect Pro | 用户手册与工程使用说明书 (v1.1.0)</title>
    <style>
        :root {{
            --primary: #0284C7;
            --primary-hover: #0369A1;
            --primary-light: #F0F9FF;
            --primary-border: #BAE6FD;
            --dark: #0F172A;
            --slate-800: #1E293B;
            --slate-600: #475569;
            --slate-400: #94A3B8;
            --slate-200: #E2E8F0;
            --slate-100: #F1F5F9;
            --slate-50: #F8FAFC;
            --success: #059669;
            --success-light: #ECFDF5;
            --warning: #D97706;
            --warning-light: #FFFBEB;
            --danger: #DC2626;
            --danger-light: #FEF2F2;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Microsoft YaHei", sans-serif;
            font-size: 15px;
            line-height: 1.75;
            color: var(--slate-800);
            background-color: var(--slate-100);
            padding: 24px 16px;
        }}

        .page-container {{
            max-width: 1080px;
            margin: 0 auto;
            background: #FFFFFF;
            border-radius: 12px;
            border: 1px solid var(--slate-200);
            box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
            padding: 48px 56px;
        }}

        /* 顶部工业徽章头 */
        .manual-top-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid var(--primary-border);
            padding-bottom: 16px;
            margin-bottom: 32px;
        }}
        .manual-top-bar .platform-title {{
            font-size: 13px;
            font-weight: 700;
            color: var(--primary);
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .manual-top-bar .doc-version {{
            font-size: 12px;
            color: var(--slate-600);
            background: var(--slate-100);
            padding: 4px 12px;
            border-radius: 20px;
            font-weight: 600;
            border: 1px solid var(--slate-200);
        }}

        /* 标题层级排版 */
        h1, h2, h3, h4, h5, h6 {{
            color: var(--dark);
            font-weight: 700;
            line-height: 1.35;
            margin-top: 1.8em;
            margin-bottom: 0.8em;
        }}
        h1 {{
            font-size: 26px;
            border-bottom: 2px solid var(--slate-200);
            padding-bottom: 12px;
            margin-top: 0.5em;
        }}
        h2 {{
            font-size: 20px;
            border-bottom: 1px solid var(--slate-200);
            padding-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        h3 {{
            font-size: 16.5px;
        }}
        h4 {{
            font-size: 15px;
        }}

        p {{
            margin-bottom: 1.1em;
        }}

        /* 链接风格 */
        a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.15s ease;
        }}
        a:hover {{
            color: var(--primary-hover);
            text-decoration: underline;
        }}

        /* 列表 */
        ul, ol {{
            margin-left: 24px;
            margin-bottom: 1.2em;
        }}
        li {{
            margin-bottom: 6px;
        }}

        /* 引用块 / Callout 强调 */
        blockquote {{
            border-left: 4px solid var(--primary);
            background: var(--primary-light);
            border-radius: 0 8px 8px 0;
            padding: 14px 20px;
            margin: 18px 0;
            color: var(--slate-800);
            font-size: 14.5px;
        }}
        blockquote p:last-child {{
            margin-bottom: 0;
        }}

        /* 工业级表格 */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0 28px 0;
            font-size: 14px;
            border: 1px solid var(--slate-200);
            border-radius: 8px;
            overflow: hidden;
            display: table;
        }}
        th {{
            background: #1E293B;
            color: #FFFFFF;
            font-weight: 600;
            text-align: left;
            padding: 12px 14px;
            border: 1px solid #334155;
            letter-spacing: 0.3px;
        }}
        td {{
            padding: 11px 14px;
            border: 1px solid var(--slate-200);
            color: var(--slate-800);
            vertical-align: middle;
        }}
        tr:nth-child(even) td {{
            background: var(--slate-50);
        }}
        tr:hover td {{
            background: #F0F9FF;
        }}

        /* 代码高亮与代码块 */
        code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            font-size: 13px;
            background: var(--slate-100);
            color: #0369A1;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid var(--slate-200);
        }}
        pre {{
            background: #0F172A;
            color: #F8FAFC;
            padding: 16px 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 18px 0 24px 0;
            border: 1px solid #334155;
        }}
        pre code {{
            background: transparent;
            color: inherit;
            border: none;
            padding: 0;
            font-size: 13px;
            line-height: 1.6;
        }}

        /* 图片与图库 */
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            margin: 12px auto;
            border-radius: 8px;
            border: 1px solid var(--slate-200);
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        img:hover {{
            transform: scale(1.01);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        }}

        /* 数学公式内联修饰 */
        .math-tex {{
            font-family: "Cambria Math", "Latin Modern Math", KaTeX_Math, "Times New Roman", serif;
            font-style: italic;
            background: #F1F5F9;
            padding: 1px 6px;
            border-radius: 4px;
            color: #0F172A;
            border: 1px solid #E2E8F0;
            font-size: 14px;
        }}

        /* 分割线 */
        hr {{
            border: none;
            height: 1px;
            background: var(--slate-200);
            margin: 36px 0;
        }}

        /* 底部版权与免责声明 */
        .manual-footer {{
            margin-top: 48px;
            border-top: 2px solid var(--slate-200);
            padding-top: 24px;
            text-align: center;
            font-size: 13px;
            color: var(--slate-600);
        }}

        /* 浮动操作按钮栏 (返回顶部与快速打印) */
        .floating-action-bar {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 1000;
        }}
        .floating-btn {{
            background: #0284C7;
            color: #FFFFFF;
            border: none;
            border-radius: 24px;
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
            text-decoration: none;
        }}
        .floating-btn:hover {{
            background: #0369A1;
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(2, 132, 199, 0.45);
            color: #FFFFFF;
            text-decoration: none;
        }}

        /* 打印机与 PDF 另存专用样式 */
        @media print {{
            body {{
                background: #FFFFFF;
                padding: 0;
            }}
            .page-container {{
                box-shadow: none;
                border: none;
                padding: 0;
                max-width: 100%;
            }}
            .floating-action-bar {{
                display: none !important;
            }}
            a {{
                color: #000000;
                text-decoration: none;
            }}
            table, pre, blockquote {{
                page-break-inside: avoid;
            }}
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 8px;
            }}
            .page-container {{
                padding: 24px 18px;
            }}
            h1 {{
                font-size: 22px;
            }}
            h2 {{
                font-size: 18px;
            }}
            .floating-action-bar {{
                bottom: 16px;
                right: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="page-container">
        <div class="manual-top-bar">
            <span class="platform-title">⚡ ANSV 微型执行器与精密传动仿真验证平台 · 官方工程指南</span>
            <span class="doc-version">Coil-Architect Pro v1.1.0 绿色免安装版</span>
        </div>

        <!-- 核心说明书正文 -->
        <article class="markdown-body">
{html_body}
        </article>

        <div class="manual-footer">
            <p><b>ANSV Coil-Architect Pro</b> · 电磁线圈多物理场仿真工作站</p>
            <p>官方技术支持网站: <a href="https://ansv.net" target="_blank">ansv.net</a> · 官方技术邮箱: support@ansv.net</p>
            <p style="margin-top: 6px; font-size: 11.5px; color: #94A3B8;">Copyright © 2026 ANSV Transmissions & Micro-Actuators Lab. All Rights Reserved.</p>
        </div>
    </div>

    <!-- 浮动操作条 -->
    <div class="floating-action-bar">
        <button class="floating-btn" onclick="window.print()" title="直接打印或无损另存为 PDF 说明书">
            🖨️ 打印 / 另存为 PDF
        </button>
        <button class="floating-btn" onclick="window.scrollTo({{ top: 0, behavior: 'smooth' }})" title="返回页面顶部">
            🔝 返回顶部
        </button>
    </div>
</body>
</html>
"""

    # 5. 输出文件保存
    for out_p in output_html_paths:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(html_document)
        size_kb = out_p.stat().st_size / 1024
        print(f"  ✓ 成功生成说明书: {out_p.name} ({size_kb:.1f} KB) -> {out_p}")

    print("\n🎉 [OK] GitHub README 说明书已 100% 成功编译为独立离线 HTML 说明书！")
    return output_html_paths[0]


if __name__ == "__main__":
    build_html_manual()
