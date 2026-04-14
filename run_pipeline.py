"""
run_pipeline.py
───────────────
MASTER RUNNER — Executes all 6 stages in order.

Run this single file to execute the complete pipeline from start to finish:
  python run_pipeline.py

Stages:
  1. Load and clean all 6 raw Excel files
  2. Merge into one master table + add derived columns
  3. Run 4-type analysis (descriptive, trend, comparative, efficiency)
  4. Forecast 7 days using 3 methods (selects best automatically)
  5. Generate 8 charts as PNG files
  6. Export Power BI-ready Excel with all sheets + guide

You can also run individual stages:
  python src/01_load_and_clean.py
  python src/02_merge_master.py
  ...etc
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def run_stage(stage_num: int, module_path: str, label: str):
    """Imports and runs the main() of a given stage script."""
    import importlib.util

    print(f"\n{'━'*60}")
    print(f"  RUNNING STAGE {stage_num}: {label}")
    print(f"{'━'*60}")

    start = time.time()

    spec   = importlib.util.spec_from_file_location(f"stage_{stage_num}", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()

    elapsed = time.time() - start
    print(f"\n  Stage {stage_num} completed in {elapsed:.1f}s")


def main():
    print("╔" + "═"*58 + "╗")
    print("║   BuildINT Energy Intelligence — Full Pipeline Runner   ║")
    print("╚" + "═"*58 + "╝")

    src = ROOT / "src"

    stages = [
        (1, str(src / "01_load_and_clean.py"),    "Load & Clean Raw Data"),
        (2, str(src / "02_merge_master.py"),       "Merge Master Table"),
        (3, str(src / "03_analyse.py"),            "Analysis"),
        (4, str(src / "04_forecast.py"),           "Forecasting"),
        (5, str(src / "05_charts.py"),             "Chart Generation"),
        (6, str(src / "06_export_powerbi.py"),     "Power BI Export"),
    ]

    total_start = time.time()

    for stage_num, path, label in stages:
        try:
            run_stage(stage_num, path, label)
        except Exception as e:
            print(f"\n  ❌ ERROR in Stage {stage_num}: {e}")
            print("  Fix the error and re-run from this stage:")
            print(f"    python src/{Path(path).name}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    total = time.time() - total_start

    print("\n" + "╔" + "═"*58 + "╗")
    print(f"║   ✅ ALL STAGES COMPLETE in {total:.1f}s" + " " * (30 - len(f"{total:.1f}")) + "║")
    print("╚" + "═"*58 + "╝")

    print("""
  DELIVERABLES:
  ┌─────────────────────────────────────────────────────┐
  │  📊 data/outputs/BuildINT_PowerBI_Data.xlsx         │
  │     → Open this in Power BI Desktop                 │
  │     → Follow 'PowerBI_Guide' sheet for exact steps  │
  │                                                     │
  │  📈 reports/charts/  (8 PNG charts)                 │
  │     → Paste directly into PowerPoint slides         │
  │                                                     │
  │  📦 data/processed/  (cleaned pkl files)            │
  │     → Use for any further Python analysis           │
  └─────────────────────────────────────────────────────┘

  NEXT STEPS:
  1. Open BuildINT_PowerBI_Data.xlsx in Power BI Desktop
     → Home → Get Data → Excel Workbook
  2. Build visuals using the PowerBI_Guide sheet
  3. Export Power BI to PDF
  4. Use PNG charts from reports/charts/ in your PPT
    """)


if __name__ == "__main__":
    main()