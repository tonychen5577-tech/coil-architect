# -*- coding: utf-8 -*-
import re

with open("tools/generate_html_manual.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Proactively clean any stray \% or \sim before markdown rendering
cleanup_target = '    # 3.2 将 <div align="center"> 转换为带有 markdown="1" 的响应式居中容器，支持内部表格解析'
cleanup_code = '''    # 3.2 净化可能遗留的转义符号 (如 \\% 与 \\sim)
    md_content = md_content.replace(r'\\%', '%').replace(r'\\sim', '~')

    # 3.3 将 <div align="center"> 转换为带有 markdown="1" 的响应式居中容器，支持内部表格解析'''

if cleanup_target in text:
    text = text.replace(cleanup_target, cleanup_code, 1)

# 2. Update .math-block and .math-tex styles
old_css_pattern = r'\.math-block\s*\{\{[\s\S]*?\}\}\s*/\*\s*数学公式内联修饰\s*\*/\s*\.math-tex\s*\{\{[\s\S]*?\}\}'
new_css = '''.math-block {{
            text-align: center;
            margin: 18px 0;
            padding: 14px 20px;
            background: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-left: 4px solid var(--primary);
            border-radius: 6px;
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: 15px;
            font-weight: 500;
            color: #0F172A;
            overflow-x: auto;
        }}

        /* 数学公式内联修饰 */
        .math-tex {{
            font-family: inherit;
            background: transparent;
            padding: 0 1px;
            border: none;
            color: inherit;
            font-size: inherit;
        }}'''

text = re.sub(old_css_pattern, new_css, text)

with open("tools/generate_html_manual.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated tools/generate_html_manual.py successfully!")
