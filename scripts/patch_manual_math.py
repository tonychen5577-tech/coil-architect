# -*- coding: utf-8 -*-

with open('tools/generate_html_manual.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the single braces in .math-block with double braces {{ }}
bad_css = '''        /* 块级数学公式卡片 */
        .math-block {
            text-align: center;
            margin: 16px 0;
            padding: 12px 18px;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            font-family: "Cambria Math", "Latin Modern Math", KaTeX_Math, "Times New Roman", serif;
            font-size: 15px;
            color: #0F172A;
            overflow-x: auto;
        }'''

good_css = '''        /* 块级数学公式卡片 */
        .math-block {{
            text-align: center;
            margin: 16px 0;
            padding: 12px 18px;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            font-family: "Cambria Math", "Latin Modern Math", KaTeX_Math, "Times New Roman", serif;
            font-size: 15px;
            color: #0F172A;
            overflow-x: auto;
        }}'''

bad_norm = bad_css.replace('\r\n', '\n')
good_norm = good_css.replace('\r\n', '\n')
content_norm = content.replace('\r\n', '\n')

if bad_norm in content_norm:
    content_norm = content_norm.replace(bad_norm, good_norm, 1)
    print("Fixed CSS braces in f-string.")
else:
    print("bad_norm not found!")

with open('tools/generate_html_manual.py', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(content_norm.replace('\n', '\r\n'))

print("Done.")
