"""
02_merge_master.py
──────────────────
WHAT THIS FILE DOES:
  - Loads all 6 cleaned DataFrames from data/processed/
  - Joins them all together on the 'date' column into one master table
  - Adds derived/calculated columns (totals, shares, carbon, active flag)
  - Saves master table as both .pkl and .xlsx to data/processed/

WHY ONE MASTER TABLE:
  With 6 separate files you can't see the full picture.
  A master table lets you see every device's consumption for each day
  in one row. This is the foundation of ALL analysis that follows.

HOW TO RUN:
  python src/02_merge_master.py
  (Run AFTER 01_load_and_clean.py)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import numpy as np
from config import PROCESSED_DIR, OUTPUTS_DIR, CO2_KG_PER_KWH, ACTIVE_DAY_THRESHOLD_KWH


def load_cleaned() -> dict:
    """
    Loads all cleaned pickle files from data/processed/.
    Returns a dict: key → DataFrame
    """
    keys = ["office", "front_ac", "back_ac", "lib_front", "lib_back", "libi"]
    dfs = {}
    for key in keys:
        path = PROCESSED_DIR / f"{key}_clean.pkl"
        dfs[key] = pd.read_pickle(path)
        print(f"  Loaded {key}: {dfs[key].shape}")
    return dfs


def build_master(dfs: dict) -> pd.DataFrame:
    """
    Merges all sources into one master DataFrame.

    Strategy:
      - Start with 'office' as the base (it has all 4 device categories).
      - Left-join AC savings data (adds saved/baseline columns).
      - Left-join 3 lighting files (adds kWh per lighting zone).
      - 'left' join means: keep all office dates, add matching data from others.
        If lights data doesn't have that date → NaN (we'll fill with 0).
    """
    print("\n  Building master table...")

    # ── Start with office base ────────────────────────────────────────────────
    master = dfs["office"].copy()
    # office already has: date, sockets, front_ac, back_ac, server, total

    # ── Join Front AC savings ─────────────────────────────────────────────────
    # We want: front_ac_used, front_ac_saved, front_ac_baseline
    ac_front = dfs["front_ac"][["date", "front_ac_used", "front_ac_saved", "front_ac_baseline"]].copy()
    master = master.merge(ac_front, on="date", how="left")

    # ── Join Back AC savings ──────────────────────────────────────────────────
    ac_back = dfs["back_ac"][["date", "back_ac_used", "back_ac_saved", "back_ac_baseline"]].copy()
    master = master.merge(ac_back, on="date", how="left")

    # ── Join 3 lighting sources ───────────────────────────────────────────────
    lib_f = dfs["lib_front"][["date", "lib_front_kwh"]].copy()
    lib_b = dfs["lib_back"][["date", "lib_hall_kwh"]].copy()
    lib_i = dfs["libi"][["date", "lib_back_kwh"]].copy()

    master = master.merge(lib_f, on="date", how="left")
    master = master.merge(lib_b, on="date", how="left")
    master = master.merge(lib_i, on="date", how="left")

    # ── Fill NaN with 0 for lighting (device off = 0 consumption) ────────────
    light_cols = ["lib_front_kwh", "lib_hall_kwh", "lib_back_kwh"]
    master[light_cols] = master[light_cols].fillna(0)

    return master


def add_derived_columns(master: pd.DataFrame) -> pd.DataFrame:
    """
    Adds calculated columns that don't exist in raw data but are needed for analysis.
    Each calculation is commented so you understand what and why.
    """
    print("  Adding derived columns...")

    # ── Date helper columns ───────────────────────────────────────────────────
    master["day_number"]  = range(1, len(master) + 1)           # 1,2,3...7 — used for regression
    master["day_name"]    = master["date"].dt.strftime("%a")    # Mon, Tue, Wed...
    master["is_weekend"]  = master["date"].dt.dayofweek >= 5    # Sat=5, Sun=6 → True

    # ── Total lights kWh per day ──────────────────────────────────────────────
    master["total_lights"] = (
        master["lib_front_kwh"] +
        master["lib_hall_kwh"] +
        master["lib_back_kwh"]
    )

    # ── Total AC savings (both units combined) ────────────────────────────────
    master["total_ac_saved"]    = master["front_ac_saved"].fillna(0) + master["back_ac_saved"].fillna(0)
    master["total_ac_baseline"] = master["front_ac_baseline"].fillna(0) + master["back_ac_baseline"].fillna(0)

    # ── Savings rate = what % of baseline was saved today ────────────────────
    # Formula: saved / baseline × 100
    # If baseline is 0 (data missing), savings rate = 0 to avoid division error
    master["savings_rate_pct"] = np.where(
        master["total_ac_baseline"] > 0,
        (master["total_ac_saved"] / master["total_ac_baseline"]) * 100,
        0
    ).round(2)

    # ── Carbon footprint ─────────────────────────────────────────────────────
    # India's grid emission factor: 0.82 kg CO2 per kWh (CEA 2023)
    # CO2 emitted = actual consumption × emission factor
    # CO2 saved   = energy saved × emission factor
    master["carbon_emitted_kg"] = (master["total"] * CO2_KG_PER_KWH).round(3)
    master["carbon_saved_kg"]   = (master["total_ac_saved"].fillna(0) * CO2_KG_PER_KWH).round(3)

    # ── Device % share of daily total ────────────────────────────────────────
    # Answers: "what fraction of today's bill is from each device?"
    for col, label in [("sockets", "sockets_pct"), ("front_ac", "front_ac_pct"),
                       ("back_ac", "back_ac_pct"), ("server", "server_pct")]:
        master[label] = np.where(
            master["total"] > 0,
            (master[col] / master["total"] * 100).round(1),
            0
        )

    # ── Active day flag ───────────────────────────────────────────────────────
    # If total < threshold, the office was essentially shut down.
    # We track this so averages aren't distorted by shutdown days.
    master["is_active"] = master["total"] > ACTIVE_DAY_THRESHOLD_KWH

    return master


def print_master_summary(master: pd.DataFrame):
    """
    Prints a clean summary of the master table to the console.
    This is your "sanity check" — does the data look right?
    """
    print("\n" + "═" * 70)
    print("  MASTER TABLE SUMMARY")
    print("═" * 70)

    print(f"\n  Period   : {master['date'].min().date()} → {master['date'].max().date()}")
    print(f"  Total rows: {len(master)} days")
    print(f"  Active days: {master['is_active'].sum()} | Weekend/Off: {(~master['is_active']).sum()}")

    print("\n  Daily totals (kWh):")
    display_cols = ["date", "day_name", "sockets", "front_ac", "back_ac",
                    "server", "total", "total_ac_saved", "savings_rate_pct"]
    print(master[display_cols].to_string(index=False))

    print("\n  Device contribution (period totals):")
    total_sum = master["total"].sum()
    for col, label in [("sockets","Sockets"), ("front_ac","Front AC"),
                       ("back_ac","Back AC"), ("server","Server Room"),
                       ("total_lights","All Lights")]:
        kwh = master[col].sum()
        pct = kwh / total_sum * 100
        bar = "█" * int(pct / 3)
        print(f"    {label:<15} {kwh:>7.2f} kWh  {pct:>5.1f}%  {bar}")

    print(f"\n  Total consumed : {total_sum:.2f} kWh")
    print(f"  Total saved    : {master['total_ac_saved'].sum():.2f} kWh")
    print(f"  Avg savings rate (active days): "
          f"{master.loc[master['is_active'], 'savings_rate_pct'].mean():.1f}%")
    print(f"  Carbon emitted : {master['carbon_emitted_kg'].sum():.2f} kg CO₂")
    print(f"  Carbon saved   : {master['carbon_saved_kg'].sum():.2f} kg CO₂")


def main():
    print("=" * 60)
    print("  STAGE 2: MERGE MASTER TABLE")
    print("=" * 60)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load cleaned data ─────────────────────────────────────────────────────
    dfs = load_cleaned()

    # ── Build and enrich master ───────────────────────────────────────────────
    master = build_master(dfs)
    master = add_derived_columns(master)

    # ── Print summary for verification ───────────────────────────────────────
    print_master_summary(master)

    # ── Save to processed (pickle for code) and outputs (Excel for humans) ───
    master.to_pickle(PROCESSED_DIR / "master.pkl")
    print(f"\n  Saved: data/processed/master.pkl")

    # Export to Excel for Power BI connection
    excel_path = OUTPUTS_DIR / "BuildINT_Master_Data.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        master.to_excel(writer, sheet_name="Daily_Master", index=False)

        # Summary sheet for quick human reading
        summary_data = {
            "Metric": [
                "Period",
                "Total Days",
                "Active Days",
                "Weekend / Off Days",
                "Total Consumption (kWh)",
                "Total Energy Saved (kWh)",
                "Overall Savings Rate (%)",
                "Total Carbon Emitted (kg CO2)",
                "Total Carbon Saved (kg CO2)",
                "Average Daily - All Days (kWh)",
                "Average Daily - Active Days Only (kWh)",
                "Peak Day",
                "Peak Consumption (kWh)",
                "Lowest Active Day",
                "Lowest Active Consumption (kWh)",
                "Sockets Total (kWh)",
                "Front AC Total (kWh)",
                "Back AC Total (kWh)",
                "Server Room Total (kWh)",
                "All Lights Total (kWh)",
            ],
            "Value": [
                f"{master['date'].min().date()} to {master['date'].max().date()}",
                len(master),
                int(master["is_active"].sum()),
                int((~master["is_active"]).sum()),
                round(master["total"].sum(), 2),
                round(master["total_ac_saved"].sum(), 2),
                round(master.loc[master["is_active"], "savings_rate_pct"].mean(), 1),
                round(master["carbon_emitted_kg"].sum(), 2),
                round(master["carbon_saved_kg"].sum(), 2),
                round(master["total"].mean(), 2),
                round(master.loc[master["is_active"], "total"].mean(), 2),
                master.loc[master["total"].idxmax(), "date"].strftime("%d %b %Y"),
                round(master["total"].max(), 2),
                master.loc[master[master["is_active"]]["total"].idxmin(), "date"].strftime("%d %b %Y"),
                round(master.loc[master["is_active"], "total"].min(), 2),
                round(master["sockets"].sum(), 2),
                round(master["front_ac"].sum(), 2),
                round(master["back_ac"].sum(), 2),
                round(master["server"].sum(), 2),
                round(master["total_lights"].sum(), 2),
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)

    print(f"  Saved: data/outputs/BuildINT_Master_Data.xlsx  ← connect Power BI to this")

    print("\n" + "=" * 60)
    print("  ✅ Stage 2 Complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()