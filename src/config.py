"""
config.py
─────────
Central configuration file for the BuildINT Energy Analysis pipeline.
All file paths, column names, and constants are defined here.
Change this file if your raw data filenames ever change — nothing else needs updating.
"""

from pathlib import Path

# ── Root of the project ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent   # goes up from src/ to project root

# ── Data directories ──────────────────────────────────────────────────────────
RAW_DIR       = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUTS_DIR   = ROOT / "data" / "outputs"
CHARTS_DIR    = ROOT / "reports" / "charts"

# ── Raw Excel file names (only the filename, not the full path) ───────────────
FILES = {
    "office":    "BuildINT Office_Report_2025-12-16_1103.xlsx",
    "front_ac":  "BuildINT_Front_AC_Report_202512_102522_Neon.xlsx",
    "back_ac":   "BuildINT_Back_AC_Report_202512_103147.xlsx",
    "lib_front": "LIB Front_Report_2025-12-16_1047.xlsx",
    "lib_back":  "LIB BACK_Report_2025-12-15_1943.xlsx",
    "libi":      "libi_Report_2025-12-16_1052.xlsx",
}

# ── Which sheet to read from each file ───────────────────────────────────────
SHEETS = {
    "office":    "Power Consumption",
    "front_ac":  "Power Savings",
    "back_ac":   "Power Savings",
    "lib_front": "Power Consumption",
    "lib_back":  "Power Consumption",
    "libi":      "Power Consumption",
}

# ── Column rename maps (raw name → clean name) ────────────────────────────────
# After reading, every file's columns are renamed to these consistent names.
RENAME = {
    "office": {
        "Time":                "date",
        "Socket and Others":   "sockets",
        "Front AC":            "front_ac",
        "Back AC":             "back_ac",
        "Server Room":         "server",
        "Total (kWh)":         "total",
    },
    "front_ac": {
        "Date":                "date",
        "Time":                "time",
        "Power Used (kWh)":    "front_ac_used",
        "Power Saved (kWh)":   "front_ac_saved",
        "Baseline (kWh)":      "front_ac_baseline",
    },
    "back_ac": {
        "Date":                "date",
        "Time":                "time",
        "Power Used (kWh)":    "back_ac_used",
        "Power Saved (kWh)":   "back_ac_saved",
        "Baseline (kWh)":      "back_ac_baseline",
    },
    "lib_front": {
        "Date":                "date",
        "Power (kWh)":         "lib_front_kwh",
    },
    "lib_back": {
        "Date":                "date",
        "Power (kWh)":         "lib_hall_kwh",
    },
    "libi": {
        "Date":                "date",
        "Power (kWh)":         "lib_back_kwh",
    },
}

# ── Analysis constants ────────────────────────────────────────────────────────
# A day is considered "active" if total office consumption exceeds this kWh
ACTIVE_DAY_THRESHOLD_KWH = 10.0

# CO2 emission factor for India's grid (kg CO2 per kWh) — CEA 2023 value
CO2_KG_PER_KWH = 0.82

# Forecast horizon (number of days to forecast forward)
FORECAST_DAYS = 7

# Minimum realistic forecast value (consumption can't go below this)
FORECAST_MIN_KWH = 20.0

# ── Chart styling ─────────────────────────────────────────────────────────────
COLORS = {
    "sockets":   "#4472C4",   # blue
    "front_ac":  "#ED7D31",   # orange
    "back_ac":   "#A9D18E",   # green
    "server":    "#7B7B7B",   # grey
    "lib_front": "#FFC000",   # yellow
    "lib_hall":  "#5B9BD5",   # light blue
    "lib_back":  "#70AD47",   # light green
    "forecast":  "#FF4444",   # red
    "historical":"#4472C4",   # blue
    "baseline":  "#BFBFBF",   # light grey
    "saved":     "#70AD47",   # green
}
CHART_DPI      = 150
CHART_FONTSIZE = 11
CHART_STYLE    = "seaborn-v0_8-whitegrid"