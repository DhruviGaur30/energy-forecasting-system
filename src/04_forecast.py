"""
04_forecast.py
──────────────
WHAT THIS FILE DOES:
  - Loads master table and trend analysis results
  - Runs 3 forecasting methods: Linear Regression, Moving Average, Exponential Smoothing
  - Compares them and selects the best one
  - Generates 7-day forward forecast (Dec 15–21)
  - Calculates prediction intervals (upper/lower bounds = confidence band)
  - Saves forecast to data/processed/forecast.pkl and exports to Excel sheet

THE 3 METHODS EXPLAINED:
  1. LINEAR REGRESSION  → Fits a straight trend line. Best when data has a clear slope.
  2. MOVING AVERAGE     → Average of last N days. Best when trend is flat/noisy.
  3. EXPONENTIAL SMOOTH → Like moving average but gives more weight to recent days.
                          Good for data where the most recent point matters most.

WHY WE COMPARE METHODS:
  No single method is always best. We compute each one's error on historical data
  and pick the one with lowest MAPE (Mean Absolute Percentage Error).

HOW TO RUN:
  python src/04_forecast.py
  (Run AFTER 03_analyse.py)
"""

import sys
import pickle
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import numpy as np
from scipy import stats
from config import PROCESSED_DIR, OUTPUTS_DIR, FORECAST_DAYS, FORECAST_MIN_KWH


# ══════════════════════════════════════════════════════════════════════════════
# FORECASTING METHODS
# ══════════════════════════════════════════════════════════════════════════════

def method_linear_regression(x: np.ndarray, y: np.ndarray, future_x: np.ndarray) -> dict:
    """
    LINEAR REGRESSION forecast.

    How it works:
      - Fits the equation:  y = intercept + slope × x
      - slope tells you: for every 1 day increase, consumption changes by 'slope' kWh
      - intercept is the predicted value at day 0 (the starting point)
      - R² measures how well the line fits the actual data (1.0 = perfect)

    Prediction interval:
      - We compute the standard error of the forecast (se_fit)
      - Upper = forecast + 1.5 × se_fit  (optimistic scenario)
      - Lower = forecast − 1.5 × se_fit  (pessimistic scenario)
      - The band shows "how wrong we might be"
    """
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    # Historical fit (what the model says for known dates)
    y_hat = intercept + slope * x

    # MAPE on historical data = our "accuracy score"
    mape = np.mean(np.abs((y - y_hat) / y)) * 100

    # Forecast for future dates
    forecast = intercept + slope * future_x
    forecast = np.maximum(forecast, FORECAST_MIN_KWH)  # floor at minimum

    # Prediction interval (approximate)
    n = len(x)
    x_mean = x.mean()
    se_fit = std_err * np.sqrt(1 + 1/n + (future_x - x_mean)**2 / np.sum((x - x_mean)**2))
    upper  = forecast + 1.5 * se_fit
    lower  = np.maximum(forecast - 1.5 * se_fit, FORECAST_MIN_KWH)

    return {
        "name":        "Linear Regression",
        "slope":       round(slope, 4),
        "intercept":   round(intercept, 4),
        "r_squared":   round(r_value**2, 4),
        "mape_pct":    round(mape, 2),
        "forecast":    [round(v, 2) for v in forecast],
        "upper":       [round(v, 2) for v in upper],
        "lower":       [round(v, 2) for v in lower],
        "y_hat":       [round(v, 2) for v in y_hat],
    }


def method_moving_average(y: np.ndarray, window: int = 3, n_periods: int = 7) -> dict:
    """
    SIMPLE MOVING AVERAGE forecast.

    How it works:
      - Takes the average of the last `window` observations
      - Uses that same average for ALL future periods
      - Simple but ignores trends entirely

    When to use:
      - Data is noisy with no clear trend
      - You don't have enough data to fit a regression
    """
    if len(y) < window:
        window = len(y)

    last_n = y[-window:]
    avg = last_n.mean()

    # Compute on rolling windows to get MAPE
    y_hat = np.array([y[:max(1, i)].mean() for i in range(1, len(y)+1)])
    mape = np.mean(np.abs((y - y_hat) / np.where(y > 0, y, 1))) * 100

    forecast = np.array([max(avg, FORECAST_MIN_KWH)] * n_periods)
    std_dev = y.std()
    upper = forecast + 1.5 * std_dev
    lower = np.maximum(forecast - 1.5 * std_dev, FORECAST_MIN_KWH)

    return {
        "name":     f"Moving Average (window={window})",
        "window":   window,
        "avg":      round(avg, 2),
        "mape_pct": round(mape, 2),
        "forecast": [round(v, 2) for v in forecast],
        "upper":    [round(v, 2) for v in upper],
        "lower":    [round(v, 2) for v in lower],
    }


def method_exponential_smoothing(y: np.ndarray, alpha: float = 0.4, n_periods: int = 7) -> dict:
    """
    EXPONENTIAL SMOOTHING forecast.

    How it works:
      - Smoothed value = alpha × actual + (1 - alpha) × previous_smoothed
      - alpha = 0 → only uses old history (ignores new data)
      - alpha = 1 → only uses the very latest point
      - alpha = 0.4 is a common starting point: balances old and new

    When to use:
      - Data has a declining or increasing trend
      - You want recent days to matter more than older days
      - Good for this dataset (clear declining trend in active days)
    """
    smoothed = np.zeros(len(y))
    smoothed[0] = y[0]

    for i in range(1, len(y)):
        smoothed[i] = alpha * y[i] + (1 - alpha) * smoothed[i-1]

    mape = np.mean(np.abs((y - smoothed) / np.where(y > 0, y, 1))) * 100

    last = smoothed[-1]
    forecast = np.array([max(last, FORECAST_MIN_KWH)] * n_periods)
    std_dev = y.std()
    upper = forecast + 1.5 * std_dev
    lower = np.maximum(forecast - 1.5 * std_dev, FORECAST_MIN_KWH)

    return {
        "name":     f"Exponential Smoothing (α={alpha})",
        "alpha":    alpha,
        "mape_pct": round(mape, 2),
        "forecast": [round(v, 2) for v in forecast],
        "upper":    [round(v, 2) for v in upper],
        "lower":    [round(v, 2) for v in lower],
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN FORECAST LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def generate_forecast(master: pd.DataFrame) -> dict:
    """
    Runs all 3 methods, compares them, picks the best, returns full forecast package.
    """
    print("\n  ── Setting up forecast data ──────────────────────────────")

    # ── Use ACTIVE days only ──────────────────────────────────────────────────
    # WHY: Weekend/shutdown days (Dec 13–14) are behavioral outliers.
    # Including them would make the trend look steeper than it really is.
    # CAVEAT: This assumes weekday patterns continue. Must state this assumption.
    active = master[master["is_active"]].copy().reset_index(drop=True)

    x = active["day_number"].values.astype(float)  # [1, 2, 3, 4, 5]
    y = active["total"].values.astype(float)         # actual kWh values

    print(f"  Active days used for fitting: {len(active)}")
    for i, (xi, yi, date) in enumerate(zip(x, y, active["date"])):
        print(f"    Day {int(xi)} | {date.strftime('%d %b (%a)')} | {yi:.2f} kWh")

    # ── Future day numbers and dates ──────────────────────────────────────────
    last_date = master["date"].max()
    last_day  = master["day_number"].max()

    future_x     = np.arange(last_day + 1, last_day + FORECAST_DAYS + 1, dtype=float)
    future_dates = [last_date + datetime.timedelta(days=i+1) for i in range(FORECAST_DAYS)]

    print(f"\n  Forecasting {FORECAST_DAYS} days: "
          f"{future_dates[0].strftime('%d %b')} → {future_dates[-1].strftime('%d %b')}")

    # ── Run all 3 methods ─────────────────────────────────────────────────────
    print("\n  ── Running forecasting methods ───────────────────────────")

    lr  = method_linear_regression(x, y, future_x)
    ma  = method_moving_average(y, window=3, n_periods=FORECAST_DAYS)
    es  = method_exponential_smoothing(y, alpha=0.4, n_periods=FORECAST_DAYS)

    methods = [lr, ma, es]

    print(f"\n  {'Method':<40} {'MAPE%':>6}  {'Best?'}")
    print(f"  {'─'*55}")
    best_method = min(methods, key=lambda m: m["mape_pct"])
    for m in methods:
        marker = "  ← SELECTED" if m["name"] == best_method["name"] else ""
        print(f"  {m['name']:<40} {m['mape_pct']:>5.1f}%{marker}")

    # ── Build forecast DataFrame ──────────────────────────────────────────────
    forecast_df = pd.DataFrame({
        "date":         future_dates,
        "day_number":   future_x,
        "day_name":     [d.strftime("%a") for d in future_dates],
        "is_weekend":   [d.weekday() >= 5 for d in future_dates],
        "forecast_kwh": best_method["forecast"],
        "upper_kwh":    best_method["upper"],
        "lower_kwh":    best_method["lower"],
        "method":       best_method["name"],
    })

    # ── Adjust weekends in forecast ───────────────────────────────────────────
    # WHY: We know from Dec 13–14 that weekends see ~80% less consumption.
    # Forecasting weekends the same as weekdays would be misleading.
    WEEKEND_FACTOR = 0.20  # weekends = ~20% of weekday consumption
    for i, row in forecast_df.iterrows():
        if row["is_weekend"]:
            forecast_df.at[i, "forecast_kwh"] = round(row["forecast_kwh"] * WEEKEND_FACTOR, 2)
            forecast_df.at[i, "upper_kwh"]    = round(row["upper_kwh"] * WEEKEND_FACTOR, 2)
            forecast_df.at[i, "lower_kwh"]    = round(row["lower_kwh"] * WEEKEND_FACTOR, 2)

    print(f"\n  7-Day Forecast ({best_method['name']}):")
    print(f"  {'Date':<18} {'Day':<5} {'Forecast':>10} {'Low':>8} {'High':>8}  {'Note'}")
    print(f"  {'─'*65}")
    for _, row in forecast_df.iterrows():
        note = "Weekend (shutdown assumed)" if row["is_weekend"] else ""
        print(f"  {row['date'].strftime('%d %b %Y'):<18} {row['day_name']:<5} "
              f"{row['forecast_kwh']:>9.2f}  "
              f"{row['lower_kwh']:>7.2f}  "
              f"{row['upper_kwh']:>7.2f}  {note}")

    # ── Build historical line for chart overlay ───────────────────────────────
    historical_df = master[["date", "day_number", "day_name", "total", "is_active"]].copy()
    historical_df = historical_df.rename(columns={"total": "actual_kwh"})

    # ── Package everything ────────────────────────────────────────────────────
    package = {
        "forecast_df":     forecast_df,
        "historical_df":   historical_df,
        "active_x":        x.tolist(),
        "active_y":        y.tolist(),
        "active_dates":    active["date"].dt.strftime("%d %b").tolist(),
        "best_method":     best_method,
        "all_methods":     methods,
        "assumptions": [
            "Forecast built using active (weekday) days only — Dec 08–12",
            f"Method selected: {best_method['name']} (lowest MAPE: {best_method['mape_pct']}%)",
            "Weekend consumption adjusted to 20% of weekday forecast (based on Dec 13–14 observed behavior)",
            "Server room load excluded from trend — treated as fixed baseline (~6.9 kWh/day)",
            "Forecast accuracy improves with more historical data — R² will increase beyond 7 data points",
            f"Confidence band: ±1.5 standard errors of the regression",
        ],
    }

    return package


def main():
    print("=" * 60)
    print("  STAGE 4: FORECASTING")
    print("=" * 60)

    master = pd.read_pickle(PROCESSED_DIR / "master.pkl")

    package = generate_forecast(master)

    # Save forecast package
    with open(PROCESSED_DIR / "forecast.pkl", "wb") as f:
        pickle.dump(package, f)

    # Export forecast to Excel (new sheet in master file)
    excel_path = OUTPUTS_DIR / "BuildINT_Master_Data.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a",
                        if_sheet_exists="replace") as writer:
        package["forecast_df"].to_excel(writer, sheet_name="Forecast_7Day", index=False)
        package["historical_df"].to_excel(writer, sheet_name="Historical", index=False)

        # Assumptions sheet
        pd.DataFrame({"Assumptions": package["assumptions"]}).to_excel(
            writer, sheet_name="Forecast_Assumptions", index=False
        )

    print(f"\n  Saved forecast to: data/processed/forecast.pkl")
    print(f"  Exported sheets to: data/outputs/BuildINT_Master_Data.xlsx")

    print("\n" + "=" * 60)
    print("  ✅ Stage 4 Complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()