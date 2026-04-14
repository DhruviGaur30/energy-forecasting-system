"""
01_load_and_clean.py
────────────────────
WHAT THIS FILE DOES:
  - Reads each of the 6 raw Excel files
  - Validates what columns and data were actually found
  - Renames columns to consistent clean names
  - Converts dates and numbers to proper data types
  - Flags data quality issues (nulls, zeros, spikes)
  - Saves one clean .pkl (pickle) file per source into data/processed/

WHY WE DO THIS FIRST:
  Never analyse dirty data. This stage is the "washing" stage.
  If anything is wrong in your raw files, this script tells you immediately.
  Every subsequent script trusts that this step ran successfully.

HOW TO RUN:
  From project root:  python src/01_load_and_clean.py
"""

import sys
from pathlib import Path

# ── Add project root to sys.path so we can import config ─────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import numpy as np
from config import (
    RAW_DIR, PROCESSED_DIR, FILES, SHEETS, RENAME, ACTIVE_DAY_THRESHOLD_KWH
)


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def read_raw(key: str) -> pd.DataFrame:
    """
    Reads a single Excel file by its config key.
    Returns the raw DataFrame with a printed preview.
    """
    path = RAW_DIR / FILES[key]
    sheet = SHEETS[key]

    print(f"\n{'─'*60}")
    print(f"  Reading: {FILES[key]}")
    print(f"  Sheet  : {sheet}")

    df = pd.read_excel(path, sheet_name=sheet)

    print(f"  Shape  : {df.shape}  (rows × columns)")
    print(f"  Columns: {df.columns.tolist()}")
    print(f"\n  First 3 rows:")
    print(df.head(3).to_string(index=False))

    return df


def clean_dates(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """
    Converts a date column to proper datetime.
    Handles both DD-MM-YYYY (AC files) and YYYY-MM-DD (lights files) formats,
    and also 'DD Mon YYYY HH:MM' format (office file).
    """
    # Try multiple formats. pd.to_datetime is smart enough with dayfirst hint.
    df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    bad_dates = df[col].isnull().sum()
    if bad_dates > 0:
        print(f"  ⚠  WARNING: {bad_dates} date(s) could not be parsed → set to NaT")

    # Normalize to date only (remove time component)
    df[col] = df[col].dt.normalize()

    return df


def clean_numbers(df: pd.DataFrame, exclude: list = None) -> pd.DataFrame:
    """
    Converts all columns (except 'date' and any in exclude list) to float.
    Non-numeric values become NaN so they are visible and trackable.
    """
    exclude = exclude or []
    skip = ["date", "time"] + exclude

    for col in df.columns:
        if col not in skip:
            before_nulls = df[col].isnull().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            after_nulls = df[col].isnull().sum()
            new_nulls = after_nulls - before_nulls
            if new_nulls > 0:
                print(f"  ⚠  Column '{col}': {new_nulls} value(s) could not convert to number → NaN")

    return df


def rename_columns(df: pd.DataFrame, key: str) -> pd.DataFrame:
    """
    Applies the rename map from config.py to standardize column names.
    """
    rename_map = RENAME[key]
    df = df.rename(columns=rename_map)
    return df


def data_quality_report(df: pd.DataFrame, name: str):
    """
    Prints a simple data quality summary.
    Checks: nulls, zeros, statistical outliers (values beyond 3 std devs).
    """
    print(f"\n  📋 Data Quality Report — {name}")
    print(f"     Rows       : {len(df)}")
    print(f"     Date range : {df['date'].min().date()} → {df['date'].max().date()}")

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in num_cols:
        nulls  = df[col].isnull().sum()
        zeros  = (df[col] == 0).sum()
        mean   = df[col].mean()
        std    = df[col].std()
        spikes = ((df[col] - mean).abs() > 3 * std).sum() if std > 0 else 0

        flags = []
        if nulls  > 0: flags.append(f"⚠  {nulls} nulls")
        if zeros  > 0: flags.append(f"ℹ  {zeros} zeros (verify if real shutdown)")
        if spikes > 0: flags.append(f"⚠  {spikes} statistical spikes")

        flag_str = " | ".join(flags) if flags else "✅ clean"
        print(f"     {col:<25} {flag_str}")


# ══════════════════════════════════════════════════════════════════════════════
# CLEANING FUNCTIONS PER SOURCE
# ══════════════════════════════════════════════════════════════════════════════

def clean_office() -> pd.DataFrame:
    """
    Reads and cleans the BuildINT Office rollup file.
    This is the main file — has daily totals for all 4 device categories.
    """
    df = read_raw("office")

    # The office file has all data in the first sheet with proper headers
    df = rename_columns(df, "office")
    df = clean_dates(df, "date")
    df = clean_numbers(df)
    df = df.sort_values("date").reset_index(drop=True)

    data_quality_report(df, "Office Rollup")

    return df


def clean_front_ac() -> pd.DataFrame:
    """
    Reads and cleans the Front AC unit — Power Savings sheet.
    Contains: Power Used, Power Saved, Baseline per day.
    """
    df = read_raw("front_ac")

    df = rename_columns(df, "front_ac")
    df = clean_dates(df, "date")
    df = clean_numbers(df, exclude=["time"])

    # Drop the 'time' column — it's always 00:00 (daily aggregation)
    if "time" in df.columns:
        df = df.drop(columns=["time"])

    df = df.sort_values("date").reset_index(drop=True)

    data_quality_report(df, "Front AC")

    return df


def clean_back_ac() -> pd.DataFrame:
    """
    Reads and cleans the Back AC unit — Power Savings sheet.
    Same structure as front_ac but different baseline (58.333 kWh vs 62.833).
    """
    df = read_raw("back_ac")

    df = rename_columns(df, "back_ac")
    df = clean_dates(df, "date")
    df = clean_numbers(df, exclude=["time"])

    if "time" in df.columns:
        df = df.drop(columns=["time"])

    df = df.sort_values("date").reset_index(drop=True)

    data_quality_report(df, "Back AC")

    return df


def clean_lights(key: str, label: str) -> pd.DataFrame:
    """
    Generic cleaner for the 3 lighting files (lib_front, lib_back, libi).
    They all have the same 2-column structure: Date, Power (kWh).
    """
    df = read_raw(key)

    df = rename_columns(df, key)
    df = clean_dates(df, "date")
    df = clean_numbers(df)
    df = df.sort_values("date").reset_index(drop=True)

    data_quality_report(df, label)

    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — runs when you execute this file directly
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  STAGE 1: LOAD AND CLEAN")
    print("=" * 60)

    # Ensure output directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # ── Clean each source ─────────────────────────────────────────────────────
    office    = clean_office()
    front_ac  = clean_front_ac()
    back_ac   = clean_back_ac()
    lib_front = clean_lights("lib_front", "LIB Front (Front Area Lights)")
    lib_back  = clean_lights("lib_back",  "LIB Back (Hall/Lobby Lights)")
    libi      = clean_lights("libi",      "LIBi (Back Area Lights)")

    # ── Save cleaned DataFrames to processed/ ─────────────────────────────────
    # We use .pkl (pickle) format because it preserves data types perfectly.
    # Excel would lose datetime types; CSV doesn't preserve column dtypes.
    office.to_pickle(PROCESSED_DIR / "office_clean.pkl")
    front_ac.to_pickle(PROCESSED_DIR / "front_ac_clean.pkl")
    back_ac.to_pickle(PROCESSED_DIR / "back_ac_clean.pkl")
    lib_front.to_pickle(PROCESSED_DIR / "lib_front_clean.pkl")
    lib_back.to_pickle(PROCESSED_DIR / "lib_back_clean.pkl")
    libi.to_pickle(PROCESSED_DIR / "libi_clean.pkl")

    print("\n" + "=" * 60)
    print("  ✅ Stage 1 Complete. Saved 6 cleaned files to data/processed/")
    print("=" * 60)

    # ── Quick sanity check printout ───────────────────────────────────────────
    print("\n  OFFICE TABLE (cleaned):")
    print(office.to_string(index=False))

    print("\n  FRONT AC TABLE (cleaned):")
    print(front_ac.to_string(index=False))


if __name__ == "__main__":
    main()