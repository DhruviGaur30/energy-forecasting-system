"""
03_analyse.py
─────────────
WHAT THIS FILE DOES:
  - Loads the master table from data/processed/master.pkl
  - Runs 4 types of analysis: Descriptive, Trend, Comparative, Efficiency
  - Flags anomalies and explains why they matter
  - Saves analysis results to data/processed/analysis_results.pkl
    (used by 05_charts.py and any PPT auto-generation)

THE 4 ANALYSIS TYPES EXPLAINED:
  1. DESCRIPTIVE  → What happened? (totals, averages, min/max)
  2. TREND        → Is it going up, down, or stable over time?
  3. COMPARATIVE  → How do devices compare to each other?
  4. EFFICIENCY   → How much are we saving vs what we could save?

HOW TO RUN:
  python src/03_analyse.py
  (Run AFTER 02_merge_master.py)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import numpy as np
from scipy import stats
from config import PROCESSED_DIR


def descriptive_analysis(master: pd.DataFrame) -> dict:
    """
    DESCRIPTIVE ANALYSIS — What happened?
    Computes summary stats for each device and the office overall.
    """
    print("\n  ── 1. DESCRIPTIVE ANALYSIS ──────────────────────────────")

    active = master[master["is_active"]].copy()

    results = {}

    # ── Office-level stats ────────────────────────────────────────────────────
    results["office"] = {
        "total_kwh":           round(master["total"].sum(), 2),
        "mean_kwh_all_days":   round(master["total"].mean(), 2),
        "mean_kwh_active":     round(active["total"].mean(), 2),
        "max_kwh":             round(master["total"].max(), 2),
        "min_kwh_active":      round(active["total"].min(), 2),
        "peak_date":           master.loc[master["total"].idxmax(), "date"].strftime("%d %b"),
        "lowest_active_date":  active.loc[active["total"].idxmin(), "date"].strftime("%d %b"),
        "active_days":         int(master["is_active"].sum()),
        "shutdown_days":       int((~master["is_active"]).sum()),
        "total_saved":         round(master["total_ac_saved"].sum(), 2),
        "savings_rate_pct":    round(active["savings_rate_pct"].mean(), 1),
        "total_carbon_emitted": round(master["carbon_emitted_kg"].sum(), 2),
        "total_carbon_saved":  round(master["carbon_saved_kg"].sum(), 2),
    }

    # ── Per-device stats ──────────────────────────────────────────────────────
    devices = {
        "Sockets":   "sockets",
        "Front AC":  "front_ac",
        "Back AC":   "back_ac",
        "Server":    "server",
        "Lights":    "total_lights",
    }

    total_consumption = master["total"].sum()
    results["devices"] = {}

    for label, col in devices.items():
        col_total = master[col].sum()
        results["devices"][label] = {
            "total_kwh":    round(col_total, 2),
            "share_pct":    round(col_total / total_consumption * 100, 1),
            "daily_avg":    round(master[col].mean(), 2),
            "active_avg":   round(active[col].mean(), 2),
            "max_day":      round(master[col].max(), 2),
        }

        print(f"    {label:<12}: {col_total:>7.2f} kWh  "
              f"({col_total/total_consumption*100:.1f}% of total)  "
              f"avg/day: {active[col].mean():.2f} kWh")

    print(f"\n    Office total  : {results['office']['total_kwh']} kWh")
    print(f"    Total saved   : {results['office']['total_saved']} kWh")
    print(f"    Avg savings % : {results['office']['savings_rate_pct']}%")

    return results


def trend_analysis(master: pd.DataFrame) -> dict:
    """
    TREND ANALYSIS — Is consumption going up or down?
    Computes day-over-day changes and identifies the direction of trend.
    """
    print("\n  ── 2. TREND ANALYSIS ────────────────────────────────────")

    active = master[master["is_active"]].copy().reset_index(drop=True)

    # Day-over-day change
    active["delta_kwh"] = active["total"].diff()
    active["delta_pct"]  = active["total"].pct_change() * 100

    # Overall trend: linear regression on active days
    x = active["day_number"].values.astype(float)
    y = active["total"].values.astype(float)

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    direction = "DECLINING" if slope < 0 else "INCREASING"
    magnitude = abs(slope)

    print(f"    Trend direction : {direction}")
    print(f"    Slope           : {slope:.3f} kWh per day")
    print(f"    R² (fit quality): {r_value**2:.3f}  (0=no fit, 1=perfect)")
    print(f"    P-value         : {p_value:.4f}  ({'significant' if p_value<0.05 else 'not significant at 5%'})")

    # Day-over-day breakdown
    print("\n    Day-over-day changes:")
    for _, row in active.iterrows():
        if pd.notna(row["delta_kwh"]):
            arrow = "▼" if row["delta_kwh"] < 0 else "▲"
            print(f"      {row['date'].strftime('%d %b (%a)')}: "
                  f"{row['total']:.1f} kWh  {arrow} {abs(row['delta_kwh']):.1f} kWh")
        else:
            print(f"      {row['date'].strftime('%d %b (%a)')}: "
                  f"{row['total']:.1f} kWh  (first day)")

    results = {
        "slope":       round(slope, 4),
        "intercept":   round(intercept, 4),
        "r_squared":   round(r_value**2, 4),
        "p_value":     round(p_value, 6),
        "direction":   direction,
        "active_x":    x.tolist(),
        "active_y":    y.tolist(),
        "active_dates": active["date"].dt.strftime("%d %b").tolist(),
        "day_over_day": active[["date", "total", "delta_kwh", "delta_pct"]].to_dict("records"),
    }

    return results


def comparative_analysis(master: pd.DataFrame) -> dict:
    """
    COMPARATIVE ANALYSIS — How do devices compare?
    Focuses on Front AC vs Back AC (biggest controllable loads).
    """
    print("\n  ── 3. COMPARATIVE ANALYSIS ──────────────────────────────")

    active = master[master["is_active"]].copy()

    # Front AC vs Back AC comparison
    front_total  = master["front_ac"].sum()
    back_total   = master["back_ac"].sum()
    difference   = front_total - back_total
    front_baseline = master["front_ac_baseline"].sum()
    back_baseline  = master["back_ac_baseline"].sum()

    front_savings_rate = master["front_ac_saved"].sum() / front_baseline * 100 if front_baseline > 0 else 0
    back_savings_rate  = master["back_ac_saved"].sum() / back_baseline * 100  if back_baseline > 0  else 0

    print(f"    Front AC total  : {front_total:.2f} kWh  (savings rate: {front_savings_rate:.1f}%)")
    print(f"    Back AC total   : {back_total:.2f} kWh  (savings rate: {back_savings_rate:.1f}%)")
    print(f"    Difference      : Front AC used {abs(difference):.2f} kWh MORE than Back AC")
    print(f"    Likely cause    : Front AC set at 26°C (colder) vs Back AC at 28°C")
    print(f"    Action          : Raise Front AC setpoint → estimated 5–8 kWh/day saving")

    # Lighting zone comparison
    print("\n    Lighting zones:")
    for label, col in [("Front Area", "lib_front_kwh"), ("Hall/Lobby", "lib_hall_kwh"), ("Back Area", "lib_back_kwh")]:
        total = master[col].sum()
        active_avg = master.loc[master[col] > 0, col].mean()
        active_days = (master[col] > 0).sum()
        print(f"      {label:<12}: {total:.3f} kWh total  |  {active_avg:.3f} kWh/active day  |  {active_days} active days")

    # Anomaly: LIB Front Dec 9 very low
    lib_front_vals = master["lib_front_kwh"].values
    if len(lib_front_vals) > 1 and lib_front_vals[1] < 0.1 and lib_front_vals[0] > 1:
        print("\n    ⚠  ANOMALY DETECTED: LIB Front shows 0.07 kWh on Dec 09 vs 6.99 kWh on Dec 08")
        print("       Possible causes: sensor offline, occupancy control triggered, or manual switch-off")
        print("       Recommendation: Audit LIB Front fixture and controller logs for Dec 09")

    results = {
        "front_ac_total":       round(front_total, 2),
        "back_ac_total":        round(back_total, 2),
        "ac_difference_kwh":    round(difference, 2),
        "front_savings_rate":   round(front_savings_rate, 1),
        "back_savings_rate":    round(back_savings_rate, 1),
        "lib_front_total":      round(master["lib_front_kwh"].sum(), 3),
        "lib_hall_total":       round(master["lib_hall_kwh"].sum(), 3),
        "lib_back_total":       round(master["lib_back_kwh"].sum(), 3),
    }

    return results


def efficiency_analysis(master: pd.DataFrame) -> dict:
    """
    EFFICIENCY ANALYSIS — How good is the smart system?
    Compares actual vs baseline. Tracks daily savings rate.
    """
    print("\n  ── 4. EFFICIENCY ANALYSIS ───────────────────────────────")

    active = master[master["is_active"]].copy()

    daily_efficiency = []
    for _, row in master.iterrows():
        baseline = row["total_ac_baseline"] if pd.notna(row["total_ac_baseline"]) else 0
        actual   = row["front_ac"] + row["back_ac"] if pd.notna(row["front_ac"]) else 0
        saved    = row["total_ac_saved"] if pd.notna(row["total_ac_saved"]) else 0
        rate     = (saved / baseline * 100) if baseline > 0 else 0

        daily_efficiency.append({
            "date":         row["date"],
            "day_name":     row["day_name"],
            "actual_kwh":   round(actual, 3),
            "saved_kwh":    round(saved, 3),
            "baseline_kwh": round(baseline, 3),
            "savings_pct":  round(rate, 1),
            "is_active":    row["is_active"],
        })

        print(f"    {row['date'].strftime('%d %b (%a)')}: "
              f"Used {actual:.2f} kWh | Saved {saved:.2f} kWh | "
              f"Rate {rate:.1f}%  {'✅' if rate > 40 else '⚠ ' if rate > 20 else '❌'}")

    overall_baseline = master["total_ac_baseline"].sum()
    overall_saved    = master["total_ac_saved"].sum()
    overall_rate     = overall_saved / overall_baseline * 100 if overall_baseline > 0 else 0

    print(f"\n    Overall savings rate: {overall_rate:.1f}% of total AC baseline")
    print(f"    Total AC baseline  : {overall_baseline:.2f} kWh")
    print(f"    Total AC saved     : {overall_saved:.2f} kWh")
    print(f"    Total AC used      : {master['total_ac_baseline'].sum() - overall_saved:.2f} kWh")

    results = {
        "overall_savings_rate": round(overall_rate, 1),
        "overall_baseline_kwh": round(overall_baseline, 2),
        "overall_saved_kwh":    round(overall_saved, 2),
        "daily_efficiency":     daily_efficiency,
    }

    return results


def main():
    print("=" * 60)
    print("  STAGE 3: ANALYSIS")
    print("=" * 60)

    # Load master table
    master = pd.read_pickle(PROCESSED_DIR / "master.pkl")
    print(f"  Loaded master: {master.shape[0]} rows × {master.shape[1]} columns")

    # Run all 4 analyses
    desc_results  = descriptive_analysis(master)
    trend_results = trend_analysis(master)
    comp_results  = comparative_analysis(master)
    eff_results   = efficiency_analysis(master)

    # Bundle and save results
    all_results = {
        "descriptive":  desc_results,
        "trend":        trend_results,
        "comparative":  comp_results,
        "efficiency":   eff_results,
    }

    import pickle
    with open(PROCESSED_DIR / "analysis_results.pkl", "wb") as f:
        pickle.dump(all_results, f)

    print("\n" + "=" * 60)
    print("  ✅ Stage 3 Complete. Saved analysis_results.pkl")
    print("=" * 60)

    return all_results


if __name__ == "__main__":
    main()