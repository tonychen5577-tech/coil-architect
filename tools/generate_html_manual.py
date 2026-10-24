#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
=============================================================================
Script: tools/generate_html_manual.py
Description: 将 GitHub 官方 README.md 转换为独立离线高保真 HTML 格式使用说明书
特性：
1. [零外部依赖离线阅读] 自动将 docs/images 中的高清截图、拓扑图与二维码转为 Base64 内嵌 Data URI；
2. [纯 CSS 离线高清徽标] 自动将 Shields.io 徽标转换为 100% 离线脱网可用的超清纯 CSS Badge 药丸标签；
3. [工业级 Markdown 渲染] 支持 md_in_html 与居中块，100% 完美呈现四大形态对比表与官方联系二维码表；
4. [打印与归档友好] 内置 @media print 打印机样式，支持工程师在浏览器中直接「Ctrl+P」无损另存为 PDF 说明书；
5. [双向自动同步] 可被 build_exe.py 打包流水线直接调用，自动打包至绿色全量安装包与增量升级包根目录。
=============================================================================
"""

import os
import sys
import re
import base64
import urllib.parse
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
    md_path: Path = ROOT_DIR / "README_CN.md",
    output_html_paths: list = None,
    is_en: bool = False
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

    # 2. 将网络 Shields.io 徽标转为 100% 离线脱网可用的纯 CSS Badge 药丸标签 (彻底消灭断网红叉与乱码感)
    badge_pattern = re.compile(
        r'\[\!\[([^\]]+)\]\((https://img\.shields\.io/badge/.*?)\)\]\((https?://[^\)]+)\)'
    )
    def _convert_badge(m):
        alt = m.group(1).strip()
        raw_badge_url = m.group(2)
        link = m.group(3).strip()

        path = raw_badge_url.replace('https://img.shields.io/badge/', '').split('?')[0]
        temp = path.replace('--', '__DOUBLE_HYPHEN__')
        parts = temp.split('-')
        if len(parts) >= 3:
            color = parts[-1].lstrip('#')
            label = urllib.parse.unquote(parts[0].replace('__DOUBLE_HYPHEN__', '-'))
            val = urllib.parse.unquote('-'.join(parts[1:-1]).replace('__DOUBLE_HYPHEN__', '-'))
        elif len(parts) == 2:
            label = urllib.parse.unquote(parts[0].replace('__DOUBLE_HYPHEN__', '-'))
            val = urllib.parse.unquote(parts[1].replace('__DOUBLE_HYPHEN__', '-'))
            color = '0284C7'
        else:
            label = alt
            val = ''
            color = '0284C7'

        return (
            f'<a href="{link}" class="badge-pill" target="_blank" title="{alt}">'
            f'<span class="badge-label">{label}</span>'
            f'<span class="badge-val" style="background-color: #{color};">{val}</span>'
            f'</a>'
        )

    md_content = badge_pattern.sub(_convert_badge, md_content)
    # 将连续的 badge 自动包装为 badge-group flex 容器
    md_content = re.sub(
        r'((?:<a href="[^"]+" class="badge-pill"[^>]*>.*?</a>\s*)+)',
        r'<div class="badge-group">\1</div>',
        md_content
    )

    # 3. 预处理 HTML 标签：
    # 3.1 将 Markdown 顶部的 README.md / README_CN.md / README_EN.md 链接重写为本地离线 HTML 说明书文件名，实现浏览器内中英文说明书一键无缝互跳！
    md_content = re.sub(
        r'href=[\x22\x27]README(?:_EN)?\.md[\x22\x27]',
        'href="Coil-Architect-Pro_User_Manual.html"',
        md_content
    )
    md_content = re.sub(
        r'href=[\x22\x27]README_CN\.md[\x22\x27]',
        'href="Coil-Architect-Pro_使用说明书.html"',
        md_content
    )
    md_content = re.sub(
        r'\]\(README(?:_EN)?\.md\)',
        '](Coil-Architect-Pro_User_Manual.html)',
        md_content
    )
    md_content = re.sub(
        r'\]\(README_CN\.md\)',
        '](Coil-Architect-Pro_使用说明书.html)',
        md_content
    )

    # 3.2 将 <div align="center"> 转换为带有 markdown="1" 的响应式居中容器，支持内部表格解析
    md_content = md_content.replace('<div align="center">', '<div class="text-center" markdown="1">')

    # 4. 转换简易数学公式符号为优雅样式
    def _math_sub(m):
        raw = m.group(1)
        pretty = raw.replace(r"\times", " × ").replace(r"\cdot", " · ")
        pretty = pretty.replace(r"\text{in}", "in").replace(r"\text{corner}", "corner")
        return f'<span class="math-tex">{pretty}</span>'

    md_content = re.sub(r'\$([^\$\n]+?)\$', _math_sub, md_content)

    # 5. 使用 Markdown 扩展引擎解析核心语法 (启用 md_in_html 允许在 div 内部渲染表格与列表)
    print("[Manual] 正在编译 Markdown 为标准化语义 HTML5 节点...")
    extensions = [
        "extra",
        "tables",
        "fenced_code",
        "codehilite",
        "toc",
        "nl2br",
        "sane_lists",
        "md_in_html"
    ]
    html_body = markdown.markdown(md_content, extensions=extensions)

    # 6. 组装工业级独立发布 HTML5 模板
    lang_attr = "en" if is_en else "zh-CN"
    page_title = (
        "ANSV Coil-Architect Pro | User Manual & Engineering Guide (v1.1.0)"
        if is_en else
        "ANSV Coil-Architect Pro | 用户手册与工程使用说明书 (v1.1.0)"
    )
    top_bar_title = (
        "⚡ ANSV Actuator Numerical Simulation & Validation Platform · Official Engineering Guide"
        if is_en else
        "⚡ ANSV 微型执行器与精密传动仿真验证平台 · 官方工程指南"
    )
    top_bar_ver = (
        "Coil-Architect Pro v1.1.0 Portable Edition"
        if is_en else
        "Coil-Architect Pro v1.1.0 绿色免安装版"
    )
    footer_line1 = (
        "<p><b>ANSV Coil-Architect Pro</b> · Micro-Coil Design &amp; Electro-Thermal Simulation Workstation</p>"
        if is_en else
        "<p><b>ANSV Coil-Architect Pro</b> · 微型线圈设计与电热仿真工作站</p>"
    )
    footer_line2 = (
        '<p>Official Website: <a href="https://ansv.net" target="_blank">ansv.net</a> · Technical Support: support@ansv.net</p>'
        if is_en else
        '<p>官方技术支持网站: <a href="https://ansv.net" target="_blank">ansv.net</a> · 官方技术邮箱: support@ansv.net</p>'
    )
    print_btn_title = "Print or Save as PDF Manual" if is_en else "直接打印或无损另存为 PDF 说明书"
    print_btn_text = "🖨️ Print / Save PDF" if is_en else "🖨️ 打印 / 另存为 PDF"
    top_btn_title = "Scroll to Top" if is_en else "返回页面顶部"
    top_btn_text = "🔝 Back to Top" if is_en else "🔝 返回顶部"

    html_document = f"""<!DOCTYPE html>
<html lang="{lang_attr}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
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
        }}

        body {{
            margin: 0;
            padding: 24px;
            background-color: #F8FAFC;
            color: var(--slate-800);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "Microsoft YaHei", "PingFang SC", sans-serif;
            line-height: 1.7;
            font-size: 15px;
            -webkit-font-smoothing: antialiased;
        }}

        .page-container {{
            max-width: 1040px;
            margin: 0 auto;
            background: #FFFFFF;
            border: 1px solid var(--slate-200);
            border-radius: 12px;
            padding: 42px 48px;
            box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
        }}

        /* 顶部科技感状态横条 */
        .manual-top-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 12px;
            margin-bottom: 28px;
        }}
        .manual-top-bar .platform-title {{
            font-size: 13.5px;
            font-weight: 700;
            color: var(--primary);
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .manual-top-bar .doc-version {{
            font-size: 11.5px;
            color: var(--slate-400);
            background: var(--slate-100);
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}

        /* 居中类 */
        .text-center {{
            text-align: center;
        }}

        /* 纯 CSS 离线高清徽标 (Shield Badges) */
        .badge-group {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: center;
            gap: 8px;
            margin: 16px 0 22px 0;
        }}
        .badge-pill {{
            display: inline-flex;
            align-items: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 11.5px;
            font-weight: 600;
            line-height: 1.4;
            text-decoration: none;
            border-radius: 4px;
            overflow: hidden;
            border: 1px solid rgba(0, 0, 0, 0.1);
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .badge-pill:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 10px rgba(2, 132, 199, 0.2);
        }}
        .badge-label {{
            background-color: #334155;
            color: #FFFFFF;
            padding: 3px 8px;
            letter-spacing: 0.2px;
        }}
        .badge-val {{
            color: #FFFFFF;
            padding: 3px 9px;
            font-weight: 700;
        }}

        /* 标题层级体系 */
        h1, h2, h3, h4, h5, h6 {{
            color: var(--dark);
            font-weight: 700;
            line-height: 1.35;
        }}
        h1 {{
            font-size: 26px;
            margin-top: 10px;
            margin-bottom: 12px;
            color: var(--dark);
        }}
        h2 {{
            font-size: 20px;
            margin-top: 36px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--slate-200);
            color: #0369A1;
        }}
        h3 {{
            font-size: 16.5px;
            margin-top: 24px;
            margin-bottom: 12px;
            color: var(--slate-800);
        }}
        h4 {{
            font-size: 15px;
            margin-top: 18px;
            margin-bottom: 8px;
        }}

        p {{
            margin-top: 0;
            margin-bottom: 14px;
        }}

        a {{
            color: var(--primary);
            text-decoration: none;
            transition: color 0.15s ease;
        }}
        a:hover {{
            color: var(--primary-hover);
            text-decoration: underline;
        }}

        /* 列表 */
        ul, ol {{
            padding-left: 24px;
            margin-top: 4px;
            margin-bottom: 16px;
        }}
        li {{
            margin-bottom: 6px;
        }}

        /* 引用块与工程注意项 */
        blockquote {{
            margin: 18px 0;
            padding: 12px 18px;
            background-color: var(--primary-light);
            border-left: 4px solid var(--primary);
            border-radius: 0 6px 6px 0;
            color: var(--slate-800);
            font-size: 14px;
        }}
        blockquote p:last-child {{
            margin-bottom: 0;
        }}

        /* 工业级数据表格 */
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 22px 0 28px 0;
            font-size: 13.5px;
            border: 1px solid var(--slate-200);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
        }}
        th {{
            background: #1E293B;
            color: #FFFFFF;
            font-weight: 600;
            text-align: left;
            padding: 11px 14px;
            border-bottom: 2px solid #0F172A;
            letter-spacing: 0.3px;
        }}
        td {{
            padding: 11px 14px;
            border-bottom: 1px solid var(--slate-200);
            border-right: 1px solid var(--slate-200);
            color: var(--slate-800);
            vertical-align: middle;
        }}
        td:last-child {{
            border-right: none;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:nth-child(even) td {{
            background: var(--slate-50);
        }}
        tr:hover td {{
            background: #F0F9FF;
        }}
        table img {{
            margin: 6px auto;
            border: 1px solid var(--slate-200);
            box-shadow: none;
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
            margin: 14px auto;
            border-radius: 8px;
            border: 1px solid var(--slate-200);
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        img:hover {{
            transform: scale(1.008);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        }}

        /* 数学公式内联修饰 */
        .math-tex {{
            font-family: "Cambria Math", "Latin Modern Math", KaTeX_Math, "Times New Roman", serif;
            font-style: italic;
            background: #F1F5F9;
            padding: 1px 6px;
            border-radius: 3px;
            color: #0F172A;
            font-size: 14px;
            margin: 0 2px;
            border: 1px solid #E2E8F0;
        }}

        /* 水平分割线 */
        hr {{
            border: none;
            height: 1px;
            background-color: var(--slate-200);
            margin: 36px 0;
        }}

        /* 页面底部 */
        .manual-footer {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid var(--slate-200);
            text-align: center;
            font-size: 12.5px;
            color: var(--slate-600);
        }}
        .manual-footer p {{
            margin: 4px 0;
        }}

        /* 悬浮打印与返回顶部操作条 */
        .floating-action-bar {{
            position: fixed;
            bottom: 28px;
            right: 28px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 999;
        }}
        .floating-btn {{
            background: #FFFFFF;
            color: var(--slate-800);
            border: 1px solid var(--slate-200);
            border-radius: 30px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.1);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }}
        .floating-btn:hover {{
            background: var(--primary);
            color: #FFFFFF;
            border-color: var(--primary);
            box-shadow: 0 6px 16px rgba(2, 132, 199, 0.25);
            transform: translateY(-2px);
        }}

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
            <span class="platform-title">{top_bar_title}</span>
            <span class="doc-version">{top_bar_ver}</span>
        </div>

        <!-- 核心说明书正文 -->
        <article class="markdown-body">
{html_body}
        </article>

        <div class="manual-footer">
            {footer_line1}
            {footer_line2}
            <p style="margin-top: 6px; font-size: 11.5px; color: #94A3B8;">Copyright © 2026 ANSV Transmissions & Micro-Actuators Lab. All Rights Reserved.</p>
        </div>
    </div>

    <!-- 浮动操作条 -->
    <div class="floating-action-bar">
        <button class="floating-btn" onclick="window.print()" title="{print_btn_title}">
            {print_btn_text}
        </button>
        <button class="floating-btn" onclick="window.scrollTo({{ top: 0, behavior: 'smooth' }})" title="{top_btn_title}">
            {top_btn_text}
        </button>
    </div>
</body>
</html>
"""

    # 7. 输出文件保存
    for out_p in output_html_paths:
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(html_document)
        size_kb = out_p.stat().st_size / 1024
        print(f"  ✓ 成功生成说明书: {out_p.name} ({size_kb:.1f} KB) -> {out_p}")

    print("\n🎉 [OK] GitHub README 说明书已 100% 成功编译为独立离线 HTML 说明书！")
    return output_html_paths[0]


def build_all_manuals():
    """编译英文与中文全套离线说明书"""
    print("====================================================================")
    print("  [1/2] 正在编译英文说明书 (默认主说明书): README.md -> Coil-Architect-Pro_User_Manual.html")
    print("====================================================================")
    build_html_manual(
        ROOT_DIR / "README.md",
        [
            ROOT_DIR / "docs" / "Coil-Architect-Pro_User_Manual.html",
            ROOT_DIR / "Coil-Architect-Pro_User_Manual.html",
            ROOT_DIR / "dist" / "Coil-Architect-Pro" / "Coil-Architect-Pro_User_Manual.html",
            ROOT_DIR / "dist" / "Coil-Architect-Pro" / "README_EN.html",
        ],
        is_en=True
    )
    cn_src = ROOT_DIR / "README_CN.md"
    if cn_src.exists():
        print("\n====================================================================")
        print("  [2/2] 正在编译中文说明书: README_CN.md -> Coil-Architect-Pro_使用说明书.html")
        print("====================================================================")
        build_html_manual(
            cn_src,
            [
                ROOT_DIR / "docs" / "Coil-Architect-Pro_使用说明书.html",
                ROOT_DIR / "Coil-Architect-Pro_使用说明书.html",
                ROOT_DIR / "dist" / "Coil-Architect-Pro" / "Coil-Architect-Pro_使用说明书.html",
                ROOT_DIR / "dist" / "Coil-Architect-Pro" / "README.html",
            ],
            is_en=False
        )


if __name__ == "__main__":
    build_all_manuals()

