# ENERGY CONSUMPTION ANALYSIS & FORECASTING SYSTEM
**A complete Python → Power BI → PowerPoint workflow for energy consumption analysis and forecasting**

---

## What This Project Does

Takes 6 raw Excel files from the BuildINT smart energy system (BuildINT Office, Powai — December 2025) and produces:

- A clean master dataset joining all 6 sources on date
- 4-type analysis: Descriptive, Trend, Comparative, Efficiency
- 7-day consumption forecast using 3 methods (auto-selects best)
- 8 publication-ready PNG charts
- A Power BI-ready Excel workbook with 7 structured sheets + a step-by-step guide

---

## Folder Structure

```
buildint_energy_project/
│
├── README.md                        ← You are here
├── requirements.txt                 ← Python dependencies
├── run_pipeline.py                  ← Run this to execute all 6 stages
│
├── data/
│   ├── raw/                         ← Your 6 original Excel files go here
│   │   ├── BuildINT Office_Report_2025-12-16_1103.xlsx
│   │   ├── BuildINT_Front_AC_Report_202512_102522_Neon.xlsx
│   │   ├── BuildINT_Back_AC_Report_202512_103147.xlsx
│   │   ├── LIB Front_Report_2025-12-16_1047.xlsx
│   │   ├── LIB BACK_Report_2025-12-15_1943.xlsx
│   │   └── libi_Report_2025-12-16_1052.xlsx
│   │
│   ├── processed/                   ← Auto-created: cleaned pkl files (Python intermediate)
│   │   ├── office_clean.pkl
│   │   ├── front_ac_clean.pkl
│   │   ├── back_ac_clean.pkl
│   │   ├── lib_front_clean.pkl
│   │   ├── lib_back_clean.pkl
│   │   ├── libi_clean.pkl
│   │   ├── master.pkl               ← Merged master table (all sources joined)
│   │   ├── analysis_results.pkl     ← All analysis outputs bundled
│   │   └── forecast.pkl             ← Forecast data + method comparison
│   │
│   └── outputs/                     ← Auto-created: human-readable outputs
│       ├── BuildINT_Master_Data.xlsx    ← Basic master + forecast
│       └── BuildINT_PowerBI_Data.xlsx  ← Full Power BI workbook (USE THIS)
│
├── reports/
│   ├── charts/                      ← Auto-created: 8 PNG charts
│   │   ├── 01_daily_consumption_stacked.png
│   │   ├── 02_trend_with_regression.png
│   │   ├── 03_device_share_donut.png
│   │   ├── 04_savings_vs_baseline.png
│   │   ├── 05_savings_rate.png
│   │   ├── 06_carbon_impact.png
│   │   ├── 07_lights_comparison.png
│   │   └── 08_forecast.png
│   ├── powerbi/                     ← Put your exported Power BI PDF here
│   └── ppt/                         ← Put your final PowerPoint here
│
└── src/                             ← All Python source code
    ├── config.py                    ← Central config: file names, paths, constants
    ├── 01_load_and_clean.py         ← Read + validate + clean all 6 raw files
    ├── 02_merge_master.py           ← Join all sources into 1 master table
    ├── 03_analyse.py                ← 4-type analysis + anomaly detection
    ├── 04_forecast.py               ← 3 forecast methods + auto-selection
    ├── 05_charts.py                 ← 8 PNG charts
    └── 06_export_powerbi.py         ← Power BI Excel + step-by-step guide sheet
```

---

## How to Run

### Option A — Run Everything at Once (Recommended)
```bash
# From the project root folder:
python run_pipeline.py
```
This runs all 6 stages in order. Takes about 10–15 seconds.

### Option B — Run Individual Stages
```bash
python src/01_load_and_clean.py    # Stage 1: Read + clean raw files
python src/02_merge_master.py      # Stage 2: Join into master table
python src/03_analyse.py           # Stage 3: All analysis
python src/04_forecast.py          # Stage 4: Forecasting
python src/05_charts.py            # Stage 5: Generate 8 charts
python src/06_export_powerbi.py    # Stage 6: Power BI export
```
Must be run in order — each stage depends on the previous one's output.

---

## Setup (First Time Only)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Make sure your raw Excel files are in data/raw/
# (Filenames must match exactly what's in src/config.py → FILES dict)

# 3. Run the pipeline
python run_pipeline.py
```

---

## Key Output Files

| File | What it is | Who uses it |
|------|-----------|-------------|
| `data/outputs/BuildINT_PowerBI_Data.xlsx` | 7-sheet structured workbook | Power BI |
| `reports/charts/*.png` | 8 charts (150 DPI) | PowerPoint |
| `data/processed/master.pkl` | Full master DataFrame | Further Python analysis |
| `data/processed/forecast.pkl` | Forecast package | Charts / further analysis |

---

## Configuring for New Data

If you get new data files with different names, only edit **one file**: `src/config.py`

```python
# Change the filenames here:
FILES = {
    "office":    "Your_New_Office_File.xlsx",
    "front_ac":  "Your_New_FrontAC_File.xlsx",
    ...
}
```

If column names change inside the files, update the `RENAME` dict in `config.py`.
Nothing else needs changing.

---

## What Each Stage Produces

| Stage | Script | Inputs | Outputs |
|-------|--------|--------|---------|
| 1 | `01_load_and_clean.py` | 6 raw `.xlsx` files | 6 `*_clean.pkl` files |
| 2 | `02_merge_master.py` | 6 cleaned pkls | `master.pkl`, `BuildINT_Master_Data.xlsx` |
| 3 | `03_analyse.py` | `master.pkl` | `analysis_results.pkl` (printed to console) |
| 4 | `04_forecast.py` | `master.pkl` | `forecast.pkl`, new Excel sheets |
| 5 | `05_charts.py` | `master.pkl`, `analysis_results.pkl`, `forecast.pkl` | 8 PNG charts |
| 6 | `06_export_powerbi.py` | `master.pkl`, `forecast.pkl` | `BuildINT_PowerBI_Data.xlsx` |


# After Python — Next Steps

Open Power BI Desktop (free: powerbi.microsoft.com/desktop)
Home → Get Data → Excel Workbook
Browse to data/outputs/BuildINT_PowerBI_Data.xlsx
Select all 7 sheets → Load
Follow the PowerBI_Guide sheet inside the Excel for exact visual-by-visual instructions
Export: File → Export → Export to PDF

---

## Key Findings from This Dataset

- **Total consumption**: 639.2 kWh over 7 days (Dec 08–14, 2025)
- **Overall savings rate**: 57.5% vs full-on baseline
- **Biggest load**: Sockets 42.1%, Front AC 25.5%, Back AC 24.8%
- **Weekend shutdown**: Dec 13–14 showed 80–100% savings → formalize as SOP
- **Front AC anomaly**: Uses ~4.6 kWh more than Back AC (likely 26°C vs 28°C setpoint)
- **LIB Front anomaly**: Dec 09 shows 0.07 kWh vs 6.99 on Dec 08 → sensor or control issue
- **7-day forecast**: 20–31 kWh/day weekdays, ~4 kWh weekends (Linear Regression, MAPE 20.3%)

---

## Forecast Assumptions

1. Forecast built on all 7 days (weekends included in slope — accounts for natural wind-down)
2. Linear Regression selected automatically (lowest MAPE vs Moving Average and Exponential Smoothing)
3. Weekend days adjusted to 20% of weekday baseline (based on observed Dec 13–14 behavior)
4. Forecast horizon: 7 days (Dec 15–21, 2025)
5. Confidence band: ±1.5 standard errors of regression
6. Accuracy improves significantly with more historical data (>7 data points raises R²)
