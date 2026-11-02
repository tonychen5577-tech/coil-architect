# -*- coding: utf-8 -*-
import re

files = ["README_CN.md", "README.md", "README_EN.md"]

for fn in files:
    with open(fn, "r", encoding="utf-8") as f:
        text = f.read()

    orig = text
    # Clean up standard physical units and numbers wrapped in LaTeX
    text = text.replace(r"$R < 0.020\text{ mm}$", r"$R < 0.020\text{ mm}$") # we keep formula or clean it
    
    # Specifically:
    # 1. $0.07\times 0.07 \to R=0.020\text{ mm}$ -> $0.07 \times 0.07 \to R = 0.020\text{ mm}$
    # 2. In text descriptions:
    # $0.237\text{ mm}$ -> 0.237 mm
    text = re.sub(r'\$([0-9\.]+)\\text\{\s*mm\}\$', r'\1 mm', text)
    text = re.sub(r'\$([0-9\.]+)\s*\\text\{\s*mm\}\$', r'\1 mm', text)
    # $0.2 \sim 500\text{ mm}$ -> 0.2 ~ 500 mm
    text = re.sub(r'\$([0-9\.]+)\s*\\sim\s*([0-9\.]+)\\text\{\s*mm\}\$', r'\1 ~ \2 mm', text)
    # $20,000\text{ mA}$ -> 20,000 mA
    text = re.sub(r'\$([0-9,]+)\\text\{\s*mA\}\$', r'\1 mA', text)
    # $20\text{A}$ -> 20 A
    text = re.sub(r'\$([0-9]+)\\text\{\s*A\}\$', r'\1 A', text)
    # $0.1 \sim 120\text{V}$ -> 0.1 ~ 120 V
    text = re.sub(r'\$([0-9\.]+)\s*\\sim\s*([0-9\.]+)\\text\{\s*V\}\$', r'\1 ~ \2 V', text)
    # $20^\circ\text{C}$ -> 20°C
    text = re.sub(r'\$([0-9]+)\^\\circ\\text\{\s*C\}\$', r'\1°C', text)
    text = re.sub(r'\$([0-9]+)\s*\\sim\s*([0-9]+)\^\\circ\\text\{\s*C\}\$', r'\1 ~ \2°C', text)
    # $101.7\%\text{ IACS}$ -> 101.7% IACS
    text = text.replace(r"$101.7\%\text{ IACS}$", "101.7% IACS")
    # $0.1\,\mu\text{m}$ -> 0.1 µm
    text = text.replace(r"$0.1\,\mu\text{m}$", "0.1 µm")

    # In BDV formula:
    # $$\text{BDV}_{\text{eff}} = \text{BDV}_{\text{nom}} \times \max\left(0.40, \left(\frac{R}{0.020}\right)^{0.6}\right)$$
    # keep it clean for both KaTeX and HTML parser

    if text != orig:
        with open(fn, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Updated {fn}")
    else:
        print(f"No changes in {fn}")
