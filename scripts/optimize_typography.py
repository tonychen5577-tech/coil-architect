# -*- coding: utf-8 -*-
"""
Optimize typography across README_CN.md, README.md, and README_EN.md.
Eliminates LaTeX math rendering mismatches between GitHub and local HTML help.
"""
import re

def optimize_chinese(text: str) -> str:
    # 1. Prices: replace unescaped dollar signs with USD or \$
    text = text.replace("¥4,680 / $719", "¥4,680 / USD 719")
    text = text.replace("($349)", "(USD 349)")
    text = text.replace("`($279)`", "(USD 279)")
    text = text.replace("($899)", "(USD 899)")
    text = text.replace("`($719)`", "(USD 719)")
    text = text.replace("($2,699)", "(USD 2,699)")
    text = text.replace("`($2,159)`", "(USD 2,159)")

    # 2. Temperature and ranges
    text = text.replace(r"$155^\circ\text{C}\sim 180^\circ\text{C}$", "155°C ~ 180°C")
    text = text.replace(r"155°C\sim 180°C", "155°C ~ 180°C")
    text = text.replace(r"$130\sim 170^\circ\text{C}$", "130°C ~ 170°C")
    text = text.replace(r"$70^\circ\text{C} \sim 120^\circ\text{C}$", "70°C ~ 120°C")
    text = text.replace(r"$180\sim 220^\circ\text{C}$", "180°C ~ 220°C")

    # 3. Percentages with backslashes
    text = text.replace(r"**$15.0\%$**", "**15.0%**")
    text = text.replace(r"15.0\%", "15.0%")
    text = text.replace(r"$1.0\%$", "1.0%")
    text = text.replace(r"**$3.0\%\sim 5.0\%$**", "**3.0% ~ 5.0%**")
    text = text.replace(r"$0.85\%$", "0.85%")
    text = text.replace(r"$59\%$", "59%")
    text = text.replace(r"$10\%$", "10%")
    text = text.replace(r"$20\%\sim 30\%$", "20% ~ 30%")

    # 4. Units and symbols quoted by user
    text = text.replace(r"$\mu\text{H}$", "µH")
    text = text.replace(r"$\Omega$", "Ω")
    text = text.replace(r"$\Omega/\text{m}$", "Ω/m")
    text = text.replace(r"$mm$", "mm")
    text = text.replace(r"$\text{DFM}$", "DFM")
    text = text.replace(r"$\text{HCP}$", "HCP")
    text = text.replace(r"$R_{20}$", "R₂₀")
    text = text.replace(r"$1.5\ \mu\text{m}$", "1.5 µm")
    text = text.replace(r"$7.013\ \Omega$", "7.013 Ω")
    text = text.replace(r"$7.073\ \Omega$", "7.073 Ω")
    text = text.replace(r"$\Phi 0.080$", "Φ0.080 mm")
    text = text.replace(r"$\text{Finished } KM/KG$", "Finished KM/KG")

    # 5. Numerical ranges and turns
    text = text.replace(r"$0 \sim 20,000\text{ mA}$", "0 ~ 20,000 mA")
    text = text.replace(r"$0.5 \sim 300$", "0.5 ~ 300")
    text = text.replace(r"$1 \sim 3000$", "1 ~ 3000")
    text = text.replace(r"$1920 \times 1080$", "1920 × 1080")

    # 6. Geometric relations
    text = text.replace(r"$W/H \ge 2.5$", "W/H ≥ 2.5")
    text = text.replace(r"$W/H < 2.5$", "W/H < 2.5")
    text = text.replace(r"$0.06\times 0.25$", "0.06 × 0.25")
    text = text.replace(r"$0.08\times 0.35$", "0.08 × 0.35")
    text = text.replace(r"$0.07\times 0.07$", "0.07 × 0.07")
    text = text.replace(r"$0.45\times 0.45$", "0.45 × 0.45")
    text = text.replace(r"$R = H / 2$", "R = H / 2")
    text = text.replace(r"$N = i \times j$", "N = i × j")
    text = text.replace(r"$R < 0.020\text{ mm}$", "R < 0.020 mm")
    text = text.replace(r"$\times 0.03937$", "× 0.03937")

    # 7. Subscripts / parameters in prose
    text = text.replace(r"$d$ (mm)", "d (mm)")
    text = text.replace(r"$D_{\max}$ (mm)", "D_max (mm)")
    text = text.replace(r"$R_{\text{km}}$", "R_km")
    text = text.replace(r"$L_{\text{km/kg}}$", "L_km/kg")
    text = text.replace(r"$KM/KG$", "KM/KG")
    text = text.replace(r"$F_0$", "F₀")
    text = text.replace(r"$DCR$", "DCR")
    text = text.replace(r"$D_{\max}$", "D_max")
    text = text.replace(r" $i$ ", " i ")
    text = text.replace(r" $j$ ", " j ")
    text = text.replace(r" $E$ ", " E ")

    return text

def optimize_english(text: str) -> str:
    # 1. Currency prices: escape $ as \$
    text = text.replace("saves $180, available at **$719 / ¥4,680**", r"saves \$180, available at **\$719 / ¥4,680**")
    text = text.replace("$349 (¥2,180)", r"\$349 (¥2,180)")
    text = text.replace("**$279** / seat `(¥1,744)`", r"**\$279** / seat (¥1,744)")
    text = text.replace("$899 (¥5,800)", r"\$899 (¥5,800)")
    text = text.replace("**$719** / seat `(¥4,680)`", r"**\$719** / seat (¥4,680)")
    text = text.replace("*(Save $180)*", r"*(Save \$180)*")
    text = text.replace("$2,699 (¥16,800)", r"\$2,699 (¥16,800)")
    text = text.replace("**$2,159** / seat `(¥13,440)`", r"**\$2,159** / seat (¥13,440)")
    text = text.replace("*(Save $540)*", r"*(Save \$540)*")
    text = text.replace("From $4,500/yr", r"From \$4,500/yr")

    # 2. Temperature and ranges
    text = text.replace(r"($155^\circ\text{C} \sim 180^\circ\text{C}$)", "(155°C ~ 180°C)")
    text = text.replace(r"($130\sim 170^\circ\text{C}$)", "(130°C ~ 170°C)")
    text = text.replace(r"($180\sim 220^\circ\text{C}$)", "(180°C ~ 220°C)")
    text = text.replace(r"$70^\circ\text{C} \sim 120^\circ\text{C}$", "70°C ~ 120°C")
    text = text.replace(r"$155^\circ\text{C} \sim 180^\circ\text{C}$", "155°C ~ 180°C")

    # 3. Units and symbols
    text = text.replace(r"($R_{20}$, $\mu\text{H}$, $\Omega$, $mm$, $\text{DFM}$, $\text{HCP}$, etc.)", "(R₂₀, µH, Ω, mm, DFM, HCP, etc.)")
    text = text.replace(r"$\mu\text{H}$", "µH")
    text = text.replace(r"$\Omega$", "Ω")
    text = text.replace(r"$\Omega/\text{m}$", "Ω/m")
    text = text.replace(r"$mm$", "mm")
    text = text.replace(r"$\text{DFM}$", "DFM")
    text = text.replace(r"$\text{HCP}$", "HCP")
    text = text.replace(r"$R_{20}$", "R₂₀")
    text = text.replace(r"$7.013\ \Omega$", "7.013 Ω")
    text = text.replace(r"$7.073\ \Omega$", "7.073 Ω")
    text = text.replace(r"($\text{Finished } KM/KG$)", "(Finished KM/KG)")

    # 4. Numerical ranges
    text = text.replace(r"**$1 \sim 3000$ turns**", "**1 ~ 3000 turns**")
    text = text.replace(r"**$0.5 \sim 300$ layers**", "**0.5 ~ 300 layers**")
    text = text.replace(r"$1920 \times 1080$", "1920 × 1080")

    # 5. Geometrical relations
    text = text.replace(r"$W/H \ge 2.5$", "W/H ≥ 2.5")
    text = text.replace(r"$W/H < 2.5$", "W/H < 2.5")
    text = text.replace(r"$0.06\times 0.25$", "0.06 × 0.25")
    text = text.replace(r"$0.08\times 0.35$", "0.08 × 0.35")
    text = text.replace(r"$0.07\times 0.07 \to R=0.020\text{ mm}$", "0.07 × 0.07 → R = 0.020 mm")
    text = text.replace(r"$0.45\times 0.45 \to R=0.040\text{ mm}$", "0.45 × 0.45 → R = 0.040 mm")
    text = text.replace(r"$R = H / 2$", "R = H / 2")
    text = text.replace(r"($N = i \times j$)", "(N = i × j)")
    text = text.replace(r"$R < 0.020\text{ mm}$", "R < 0.020 mm")
    text = text.replace(r"$\times 0.03937$", "× 0.03937")

    # 6. Parameters
    text = text.replace(r"$d$ (mm)", "d (mm)")
    text = text.replace(r"$D_{\max}$ (mm)", "D_max (mm)")
    text = text.replace(r"$R_{\text{km}}$", "R_km")
    text = text.replace(r"$L_{\text{km/kg}}$", "L_km/kg")
    text = text.replace(r"$T_{\text{amb}}$", "T_amb")
    text = text.replace(r"$I_{\text{drive}}$", "I_drive")
    text = text.replace(r" $h$", " h")
    text = text.replace(r" $N$", " N")
    text = text.replace(r" $R$", " R")
    text = text.replace(r" $D$", " D")
    text = text.replace(r" $I$", " I")
    text = text.replace(r" $J$", " J")
    text = text.replace(r"$\eta$", "η")
    text = text.replace(r"$\Delta$", "Δ")
    text = text.replace(r"$F_0$", "F₀")

    return text

# Run on files
with open("README_CN.md", "r", encoding="utf-8") as f:
    cn = f.read()
cn_opt = optimize_chinese(cn)
with open("README_CN.md", "w", encoding="utf-8") as f:
    f.write(cn_opt)
print("Optimized README_CN.md")

for fn in ["README.md", "README_EN.md"]:
    with open(fn, "r", encoding="utf-8") as f:
        en = f.read()
    en_opt = optimize_english(en)
    with open(fn, "w", encoding="utf-8") as f:
        f.write(en_opt)
    print(f"Optimized {fn}")
