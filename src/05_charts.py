"""
05_charts.py
────────────
WHAT THIS FILE DOES:
  - Loads master table + analysis results + forecast
  - Generates 8 publication-quality charts as PNG files
  - Saves them to reports/charts/
  - These PNGs are what you paste into PowerPoint or Power BI

CHARTS GENERATED:
  01_daily_consumption_stacked.png    → Stacked bar by device, per day
  02_trend_with_regression.png        → Scatter + regression line on active days
  03_device_share_donut.png           → Donut chart of device % contribution
  04_savings_vs_baseline.png          → Bar: actual vs baseline per day
  05_savings_rate.png                 → Line: daily savings rate %
  06_carbon_impact.png                → Dual line: emitted vs saved CO2
  07_lights_comparison.png            → Multi-line: 3 lighting zones
  08_forecast.png                     → Historical line + forecast + confidence band

HOW TO RUN:
  python src/05_charts.py
  (Run AFTER 04_forecast.py)
"""

import sys
import pickle
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend (no screen required)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import seaborn as sns

from config import PROCESSED_DIR, CHARTS_DIR, COLORS, CHART_DPI, CHART_STYLE


# ── Global chart style ─────────────────────────────────────────────────────────
plt.style.use(CHART_STYLE)
FONT = {"family": "DejaVu Sans", "size": 11}
plt.rc("font", **FONT)
plt.rc("axes", titlesize=13, titleweight="bold", labelsize=11)
plt.rcParams["axes.spines.top"]   = False
plt.rcParams["axes.spines.right"] = False

# ── Chart sizing ───────────────────────────────────────────────────────────────
WIDE = (12, 5)    # wide landscape
SQUARE = (8, 6)   # square-ish
TALL = (10, 6)    # medium tall


def save(fig, filename: str):
    path = CHARTS_DIR / filename
    fig.savefig(path, dpi=CHART_DPI, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  ✅ Saved: {filename}")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — Daily Consumption Stacked Bar
# ══════════════════════════════════════════════════════════════════════════════

def chart_daily_stacked(master: pd.DataFrame):
    fig, ax = plt.subplots(figsize=WIDE)

    labels = master["date"].dt.strftime("%d %b\n(%a)")
    x = np.arange(len(master))
    w = 0.55

    devices = [
        ("sockets",  "Sockets",    COLORS["sockets"]),
        ("front_ac", "Front AC",   COLORS["front_ac"]),
        ("back_ac",  "Back AC",    COLORS["back_ac"]),
        ("server",   "Server Rm",  COLORS["server"]),
    ]

    bottom = np.zeros(len(master))
    for col, label, color in devices:
        vals = master[col].fillna(0).values
        ax.bar(x, vals, w, bottom=bottom, label=label, color=color, alpha=0.92)
        bottom += vals

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Energy (kWh)")
    ax.set_title("Daily Energy Consumption by Device Category")
    ax.legend(loc="upper right", framealpha=0.7)

    # Annotate totals on bars
    for i, total in enumerate(master["total"]):
        ax.text(i, total + 1, f"{total:.0f}", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#333333")

    # Add weekend shading
    for i, is_wknd in enumerate(master["is_weekend"]):
        if is_wknd:
            ax.axvspan(i - 0.4, i + 0.4, alpha=0.08, color="grey", zorder=0)
            ax.text(i, -10, "Weekend", ha="center", va="top", fontsize=8,
                    color="grey", style="italic")

    ax.set_ylim(bottom=-15)
    ax.set_xlabel("Date")
    fig.tight_layout()
    save(fig, "01_daily_consumption_stacked.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2 — Trend with Regression Line
# ══════════════════════════════════════════════════════════════════════════════

def chart_trend_regression(master: pd.DataFrame, trend: dict):
    fig, ax = plt.subplots(figsize=TALL)

    # All days — scatter
    for _, row in master.iterrows():
        color = COLORS["historical"] if row["is_active"] else "lightgrey"
        marker = "o" if row["is_active"] else "x"
        ax.scatter(row["day_number"], row["total"], color=color,
                   s=90, zorder=5, marker=marker)
        ax.annotate(
            f"{row['date'].strftime('%d %b')}\n{row['total']:.0f} kWh",
            (row["day_number"], row["total"]),
            textcoords="offset points", xytext=(8, 4),
            fontsize=8, color="#444444"
        )

    # Regression line (active days only)
    x_fit = np.linspace(min(trend["active_x"]), max(trend["active_x"]), 100)
    y_fit = trend["intercept"] + trend["slope"] * x_fit
    ax.plot(x_fit, y_fit, "--", color=COLORS["forecast"], lw=2.0,
            label=f"Trend: {trend['slope']:+.1f} kWh/day  (R²={trend['r_squared']:.2f})")

    ax.set_xlabel("Day Number (from Dec 08)")
    ax.set_ylabel("Total Consumption (kWh)")
    ax.set_title("Energy Consumption Trend — Active Days")
    ax.legend(loc="upper right")

    # Insight annotation
    ax.text(0.03, 0.92, f"Trend: {trend['direction']} @ {abs(trend['slope']):.1f} kWh/day",
            transform=ax.transAxes, fontsize=10, color=COLORS["forecast"],
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=COLORS["forecast"], alpha=0.8))

    fig.tight_layout()
    save(fig, "02_trend_with_regression.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 3 — Device Share Donut
# ══════════════════════════════════════════════════════════════════════════════

def chart_device_donut(master: pd.DataFrame):
    fig, ax = plt.subplots(figsize=SQUARE)

    labels_raw = ["Sockets", "Front AC", "Back AC", "Server Rm", "Lights"]
    cols       = ["sockets", "front_ac", "back_ac", "server", "total_lights"]
    colors_raw = [COLORS["sockets"], COLORS["front_ac"], COLORS["back_ac"],
                  COLORS["server"], COLORS["lib_front"]]

    values = [master[c].sum() for c in cols]
    total  = sum(values)
    labels = [f"{l}\n{v:.1f} kWh\n({v/total*100:.1f}%)"
              for l, v in zip(labels_raw, values)]

    wedges, texts = ax.pie(
        values, labels=labels, colors=colors_raw,
        startangle=90, pctdistance=0.82,
        wedgeprops=dict(width=0.52, edgecolor="white", linewidth=2),
        textprops=dict(fontsize=9)
    )

    # Centre text
    ax.text(0, 0, f"Total\n{total:.0f} kWh", ha="center", va="center",
            fontsize=12, fontweight="bold", color="#333333")

    ax.set_title("Device Contribution — Period Total (Dec 08–14)")
    fig.tight_layout()
    save(fig, "03_device_share_donut.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 4 — Savings vs Baseline
# ══════════════════════════════════════════════════════════════════════════════

def chart_savings_vs_baseline(master: pd.DataFrame):
    fig, ax = plt.subplots(figsize=WIDE)

    labels = master["date"].dt.strftime("%d %b\n(%a)")
    x = np.arange(len(master))
    w = 0.35

    baseline = (master["front_ac_baseline"].fillna(0) + master["back_ac_baseline"].fillna(0)).values
    actual   = (master["front_ac"].fillna(0) + master["back_ac"].fillna(0)).values
    saved    = (master["total_ac_saved"].fillna(0)).values

    ax.bar(x - w/2, baseline, w, label="Baseline (No SmartSystem)",
           color=COLORS["baseline"], alpha=0.85)
    ax.bar(x + w/2, actual,   w, label="Actual Consumption",
           color=COLORS["front_ac"], alpha=0.92)

    # Savings annotation arrows
    for i, (b, a, s) in enumerate(zip(baseline, actual, saved)):
        if s > 0:
            ax.annotate("", xy=(i + w/2, a), xytext=(i - w/2, a),
                        arrowprops=dict(arrowstyle="-", color="green", lw=1.5))
            ax.text(i, max(b, a) + 2, f"↓{s:.0f}", ha="center", va="bottom",
                    fontsize=8.5, color="#1a7a1a", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Energy (kWh)")
    ax.set_title("AC Energy Saved vs Baseline")
    ax.legend(loc="upper right")
    fig.tight_layout()
    save(fig, "04_savings_vs_baseline.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 5 — Daily Savings Rate %
# ══════════════════════════════════════════════════════════════════════════════

def chart_savings_rate(master: pd.DataFrame):
    fig, ax = plt.subplots(figsize=WIDE)

    labels = master["date"].dt.strftime("%d %b\n(%a)")
    x = np.arange(len(master))
    rates = master["savings_rate_pct"].fillna(0).values

    bars = ax.bar(x, rates, 0.6, color=[
        COLORS["saved"] if r >= 40 else COLORS["front_ac"] if r >= 20 else "#e05555"
        for r in rates
    ], alpha=0.9)

    # 40% target line
    ax.axhline(40, color="#1a7a1a", ls="--", lw=1.5, label="40% target")

    for i, r in enumerate(rates):
        ax.text(i, r + 0.8, f"{r:.0f}%", ha="center", va="bottom",
                fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Savings Rate (%)")
    ax.set_ylim(0, 110)
    ax.set_title("Daily AC Energy Savings Rate vs Baseline")
    ax.legend()
    fig.tight_layout()
    save(fig, "05_savings_rate.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 6 — Carbon Impact
# ══════════════════════════════════════════════════════════════════════════════

def chart_carbon(master: pd.DataFrame):
    fig, ax = plt.subplots(figsize=TALL)

    labels = master["date"].dt.strftime("%d %b")
    x = np.arange(len(master))

    emitted = master["carbon_emitted_kg"].values
    saved   = master["carbon_saved_kg"].values

    ax.plot(x, emitted, "o-", color="#e05555", lw=2.2, ms=7, label="CO₂ Emitted (kg)")
    ax.fill_between(x, 0, emitted, alpha=0.12, color="#e05555")

    ax.plot(x, saved, "s--", color=COLORS["saved"], lw=2.2, ms=7, label="CO₂ Saved (kg)")
    ax.fill_between(x, 0, saved, alpha=0.12, color=COLORS["saved"])

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Carbon (kg CO₂)")
    ax.set_title("Daily Carbon Footprint — Emitted vs Saved")
    ax.legend()

    # Total annotations
    ax.text(0.97, 0.92, f"Total emitted: {emitted.sum():.1f} kg CO₂",
            transform=ax.transAxes, ha="right", fontsize=9,
            color="#e05555", bbox=dict(fc="white", ec="#e05555", alpha=0.7, pad=3))
    ax.text(0.97, 0.82, f"Total saved:   {saved.sum():.1f} kg CO₂",
            transform=ax.transAxes, ha="right", fontsize=9,
            color="#1a7a1a", bbox=dict(fc="white", ec="#1a7a1a", alpha=0.7, pad=3))

    fig.tight_layout()
    save(fig, "06_carbon_impact.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 7 — Lighting Zones Comparison
# ══════════════════════════════════════════════════════════════════════════════

def chart_lights(master: pd.DataFrame):
    fig, ax = plt.subplots(figsize=TALL)

    labels = master["date"].dt.strftime("%d %b")
    x = np.arange(len(master))

    zones = [
        ("lib_front_kwh", "Front Area Lights",  COLORS["lib_front"]),
        ("lib_hall_kwh",  "Hall/Lobby Lights",   COLORS["lib_hall"]),
        ("lib_back_kwh",  "Back Area Lights",    COLORS["lib_back"]),
    ]

    for col, label, color in zones:
        vals = master[col].fillna(0).values
        ax.plot(x, vals, "o-", color=color, lw=2.2, ms=7, label=label)
        ax.fill_between(x, 0, vals, alpha=0.10, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("Energy (kWh)")
    ax.set_title("Daily Lighting Consumption by Zone")
    ax.legend(loc="upper right")

    # Anomaly callout for LIB Front Dec 09
    ax.annotate("Sensor anomaly?\nOnly 0.07 kWh",
                xy=(1, master["lib_front_kwh"].iloc[1]),
                xytext=(1.5, 4),
                arrowprops=dict(arrowstyle="->", color="#e05555"),
                fontsize=8.5, color="#e05555")

    fig.tight_layout()
    save(fig, "07_lights_comparison.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 8 — Forecast with Confidence Band
# ══════════════════════════════════════════════════════════════════════════════

def chart_forecast(master: pd.DataFrame, forecast_pkg: dict):
    fig, ax = plt.subplots(figsize=WIDE)

    hist_df = forecast_pkg["historical_df"]
    fc_df   = forecast_pkg["forecast_df"]

    # Historical line
    x_hist  = np.arange(len(hist_df))
    y_hist  = hist_df["actual_kwh"].values
    labels_hist = hist_df["date"].dt.strftime("%d %b").tolist()

    ax.plot(x_hist, y_hist, "o-", color=COLORS["historical"],
            lw=2.2, ms=8, label="Historical (Actual)", zorder=5)

    # Add value labels on historical points
    for xi, yi, lbl in zip(x_hist, y_hist, labels_hist):
        ax.text(xi, yi + 2, f"{yi:.0f}", ha="center", va="bottom",
                fontsize=8.5, color=COLORS["historical"])

    # Forecast line (starts from last historical point for visual continuity)
    offset = len(hist_df) - 1                       # bridge historical → forecast
    x_fc   = np.arange(offset, offset + len(fc_df) + 1)

    # Bridge value (last historical point)
    y_fc        = np.concatenate([[y_hist[-1]], fc_df["forecast_kwh"].values])
    y_upper     = np.concatenate([[y_hist[-1]], fc_df["upper_kwh"].values])
    y_lower     = np.concatenate([[y_hist[-1]], fc_df["lower_kwh"].values])

    ax.plot(x_fc, y_fc, "s--", color=COLORS["forecast"],
            lw=2.2, ms=7, label="Forecast (7-day)", zorder=5)
    ax.fill_between(x_fc, y_lower, y_upper, alpha=0.15,
                    color=COLORS["forecast"], label="Confidence Band")

    # Forecast value labels
    for xi, yi in zip(x_fc[1:], fc_df["forecast_kwh"].values):
        ax.text(xi, yi + 2, f"{yi:.0f}", ha="center", va="bottom",
                fontsize=8.5, color=COLORS["forecast"])

    # Weekend markers in forecast
    for i, (xi, row) in enumerate(zip(x_fc[1:], fc_df.itertuples())):
        if row.is_weekend:
            ax.axvspan(xi - 0.4, xi + 0.4, alpha=0.08, color="grey", zorder=0)

    # X-axis labels
    all_labels = labels_hist + fc_df["date"].dt.strftime("%d %b").tolist()
    ax.set_xticks(np.arange(len(all_labels)))
    ax.set_xticklabels(all_labels, rotation=0, fontsize=9)

    # Divider line: historical vs forecast
    ax.axvline(offset, color="grey", ls=":", lw=1.5, alpha=0.7)
    ax.text(offset + 0.1, ax.get_ylim()[1] * 0.92, "Forecast →",
            fontsize=9, color="grey", style="italic")

    ax.set_ylabel("Total Consumption (kWh)")
    ax.set_title(f"Energy Consumption Forecast — {forecast_pkg['best_method']['name']}")
    ax.legend(loc="upper right")

    # Assumption note
    ax.text(0.02, 0.04,
            "Assumptions: weekday trend continued; weekends = 20% of weekday baseline",
            transform=ax.transAxes, fontsize=8, color="grey", style="italic")

    fig.tight_layout()
    save(fig, "08_forecast.png")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  STAGE 5: CHART GENERATION")
    print("=" * 60)

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    master = pd.read_pickle(PROCESSED_DIR / "master.pkl")

    with open(PROCESSED_DIR / "analysis_results.pkl", "rb") as f:
        analysis = pickle.load(f)

    with open(PROCESSED_DIR / "forecast.pkl", "rb") as f:
        forecast_pkg = pickle.load(f)

    print(f"  Generating charts → {CHARTS_DIR}")
    print()

    chart_daily_stacked(master)
    chart_trend_regression(master, analysis["trend"])
    chart_device_donut(master)
    chart_savings_vs_baseline(master)
    chart_savings_rate(master)
    chart_carbon(master)
    chart_lights(master)
    chart_forecast(master, forecast_pkg)

    print(f"\n  All 8 charts saved to: reports/charts/")
    print("  Next step → open reports/charts/ and paste PNGs into PowerPoint")

    print("\n" + "=" * 60)
    print("  ✅ Stage 5 Complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()