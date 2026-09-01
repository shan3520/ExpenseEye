"""
ExpenseEye Cash-Flow Forecast - Time-series forecasting of spending.

Copyright (c) 2026 Shantanu (shan3520)
Original Repository: https://github.com/shan3520/expenseeye
License: MIT

Forecasts upcoming spending from a user's transaction history.

Strategy
--------
* Aggregate expense transactions (amount < 0) into a daily and a monthly
  spending time series.
* If enough history exists (>= ~60 daily points AND >= ~6 months), fit a
  statsmodels Holt-Winters ExponentialSmoothing model (additive trend +
  weekly seasonality for the daily series). Otherwise fall back to a
  moving-average / linear-trend baseline.
* Hold out the most recent slice, forecast it, and report MAE / RMSE / MAPE
  so the accuracy of the forecast is demonstrable.

The module never raises on sparse / degenerate data: every path has a
baseline fallback and the public entry point wraps everything in try/except.
"""

import sqlite3
import warnings

import numpy as np
import pandas as pd

# statsmodels is optional at import time; we degrade gracefully if it is
# unavailable so the API never fails to boot.
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    _HAS_STATSMODELS = True
except Exception:  # pragma: no cover - defensive
    _HAS_STATSMODELS = False

# Thresholds that decide whether we have enough history for a "real" model.
_MIN_DAILY_POINTS = 60
_MIN_MONTHS = 6
_DAILY_HORIZON = 30   # forecast the next 30 days
_DAILY_HOLDOUT = 30   # hold out the most recent 30 days for accuracy

# Hard bounds on the analysis window and the serialized response.
# A statement carrying a mistyped year (1900, 2099) would otherwise build a
# continuous daily index spanning centuries -- 213k points and a ~7.7MB payload
# from a 3-row file -- which exhausts memory on a small instance. Old history is
# also worthless for a 30-day forecast, so the window is capped from the most
# recent transaction backwards.
_MAX_ANALYSIS_DAYS = 1095        # 3 years of history is ample for a 30-day forecast
_MAX_DAILY_POINTS_RETURNED = 400 # cap the serialized daily history


# --------------------------------------------------------------------------- #
# Data loading / aggregation
# --------------------------------------------------------------------------- #
def _load_expenses(db_path):
    """Return a DataFrame of expense rows (amount stored as positive spend)."""
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT txn_date, description, amount FROM transactions "
            "WHERE amount < 0 ORDER BY txn_date",
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return df
    df["txn_date"] = pd.to_datetime(df["txn_date"])
    df["spend"] = df["amount"].abs()
    return df


def _daily_series(df):
    """Daily spend total, re-indexed to a continuous date range (gaps -> 0)."""
    daily = df.groupby(df["txn_date"].dt.normalize())["spend"].sum()
    full_idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    return daily.reindex(full_idx, fill_value=0.0)


def _monthly_series(df):
    """Monthly spend total indexed by month-start timestamp."""
    monthly = df.groupby(df["txn_date"].dt.to_period("M"))["spend"].sum()
    monthly.index = monthly.index.to_timestamp()
    return monthly


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def _metrics(actual, predicted):
    """MAE / RMSE / MAPE. MAPE guards against zero actuals."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    err = predicted - actual
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))

    # MAPE only over non-zero actuals (zero-spend days make MAPE explode and
    # are not meaningful as a percentage error).
    mask = actual != 0
    if mask.any():
        mape = float(np.mean(np.abs(err[mask] / actual[mask])) * 100)
    else:
        mape = None
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2) if mape is not None else None,
    }


# --------------------------------------------------------------------------- #
# Forecast engines
# --------------------------------------------------------------------------- #
def _fit_holt_winters(train, horizon, seasonal_periods):
    """Fit Holt-Winters and forecast `horizon` steps. Returns np.ndarray."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        use_seasonal = (
            seasonal_periods is not None
            and len(train) >= 2 * seasonal_periods
        )
        model = ExponentialSmoothing(
            train,
            trend="add",
            seasonal="add" if use_seasonal else None,
            seasonal_periods=seasonal_periods if use_seasonal else None,
            initialization_method="estimated",
        )
        fit = model.fit(optimized=True)
        fc = np.asarray(fit.forecast(horizon), dtype=float)
    # Spending cannot be negative.
    return np.clip(fc, 0.0, None)


def _forecast_one_month(train_values, rich):
    """One-step-ahead monthly forecast used for rolling validation."""
    try:
        if rich and len(train_values) >= 4:
            return float(_fit_holt_winters(train_values, 1, seasonal_periods=None)[0])
        raise RuntimeError("baseline")
    except Exception:
        return float(np.mean(train_values[-3:]))


def _monthly_holdout_accuracy(monthly, rich):
    """
    Rolling one-step-ahead accuracy on the most recent months.

    Holds out the last k months; for each, trains on all prior months and
    forecasts one month ahead. Returns MAE/RMSE/MAPE on monthly totals, which
    is the meaningful accuracy for a cash-flow forecast.
    """
    vals = monthly.values.astype(float)
    n = len(vals)
    if n < 6:
        return None
    k = min(6, max(2, n // 4))
    actual, pred = [], []
    for i in range(n - k, n):
        forecast = _forecast_one_month(vals[:i], rich)
        actual.append(vals[i])
        pred.append(forecast)
    acc = _metrics(actual, pred)
    acc["holdout_months"] = int(k)
    acc["basis"] = "monthly spend, rolling one-step-ahead holdout"
    return acc


def _baseline_forecast(train, horizon):
    """Moving-average + linear-trend baseline for sparse data."""
    train = np.asarray(train, dtype=float)
    window = min(len(train), 14)
    base = float(np.mean(train[-window:])) if window else 0.0

    # Gentle linear trend from a least-squares fit over the series.
    if len(train) >= 2:
        x = np.arange(len(train))
        slope = float(np.polyfit(x, train, 1)[0])
    else:
        slope = 0.0

    steps = np.arange(1, horizon + 1)
    fc = base + slope * steps
    return np.clip(fc, 0.0, None)


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def forecast_cashflow(db_path="expenseeye.db"):
    """
    Forecast upcoming spending for the session in `db_path`.

    Returns a JSON-serializable dict:
        {
          "success": bool,
          "method": "Holt-Winters (ExponentialSmoothing)" | "Baseline ...",
          "history_days": int, "history_months": int,
          "daily": {history: [{date, spend}], forecast: [{date, spend}]},
          "monthly": {history: [{month, spend}], forecast: [{month, spend}]},
          "next_30_day_total": float,
          "next_month_total": float,
          "accuracy": {mae, rmse, mape, holdout_days, basis},
          "message": str
        }
    On any failure returns {"success": False, "error": str}.
    """
    try:
        df = _load_expenses(db_path)
        if df.empty:
            return {"success": False, "error": "No expense transactions found to forecast."}

        # Bound the analysis window to the most recent _MAX_ANALYSIS_DAYS so a
        # stray out-of-range date cannot blow up the series (see constants).
        full_span_days = int((df["txn_date"].max() - df["txn_date"].min()).days) + 1
        window_start = df["txn_date"].max() - pd.Timedelta(days=_MAX_ANALYSIS_DAYS)
        df = df[df["txn_date"] >= window_start]
        history_truncated = full_span_days > _MAX_ANALYSIS_DAYS
        if df.empty:
            return {"success": False, "error": "No expense transactions found to forecast."}

        daily = _daily_series(df)
        monthly = _monthly_series(df)
        n_days = int(len(daily))
        n_months = int(len(monthly))

        rich = (
            _HAS_STATSMODELS
            and n_days >= _MIN_DAILY_POINTS
            and n_months >= _MIN_MONTHS
        )

        # --- accuracy ------------------------------------------------------- #
        # Headline accuracy is computed at the MONTHLY level: for a cash-flow
        # forecast the quantity that matters is total spend over a period, and
        # per-day MAPE on spiky transaction data is dominated by zero-spend
        # days. We hold out the most recent months and do one-step-ahead
        # rolling forecasts. A secondary daily-holdout metric is also reported.
        accuracy = _monthly_holdout_accuracy(monthly, rich)
        daily_accuracy = None
        holdout = min(_DAILY_HOLDOUT, max(7, n_days // 5))
        if n_days > holdout + 14:
            train, test = daily.iloc[:-holdout], daily.iloc[-holdout:]
            try:
                if rich:
                    val_fc = _fit_holt_winters(train.values, len(test), seasonal_periods=7)
                else:
                    val_fc = _baseline_forecast(train.values, len(test))
            except Exception:
                val_fc = _baseline_forecast(train.values, len(test))
            daily_accuracy = _metrics(test.values, val_fc)
            daily_accuracy["holdout_days"] = int(holdout)
            daily_accuracy["basis"] = "daily spend, most-recent holdout"

        # --- final forecast on the full series ------------------------------ #
        method = "Holt-Winters (ExponentialSmoothing)"
        try:
            if rich:
                daily_fc = _fit_holt_winters(daily.values, _DAILY_HORIZON, seasonal_periods=7)
            else:
                raise RuntimeError("insufficient history")
        except Exception:
            method = "Baseline (moving-average + linear-trend)"
            daily_fc = _baseline_forecast(daily.values, _DAILY_HORIZON)

        future_idx = pd.date_range(
            daily.index[-1] + pd.Timedelta(days=1), periods=_DAILY_HORIZON, freq="D"
        )

        # Monthly forecast: prefer Holt-Winters with yearly seasonality if we
        # have >= 24 months, else seasonal-naive (avg of last 3 months).
        try:
            if rich and n_months >= 24:
                month_fc = _fit_holt_winters(monthly.values, 1, seasonal_periods=12)[0]
            else:
                raise RuntimeError("fallback to recent-average")
        except Exception:
            month_fc = float(np.mean(monthly.values[-3:]))
        month_fc = float(max(month_fc, 0.0))
        next_month_idx = (monthly.index[-1] + pd.offsets.MonthBegin(1))

        return {
            "success": True,
            "method": method,
            "history_days": n_days,
            "history_months": n_months,
            "history_truncated": history_truncated,
            "daily": {
                # Capped: the UI charts the monthly series, and an uncapped daily
                # array is the payload-amplification vector described above.
                "history_points_returned": int(min(len(daily), _MAX_DAILY_POINTS_RETURNED)),
                "history": [
                    {"date": d.strftime("%Y-%m-%d"), "spend": round(float(v), 2)}
                    for d, v in daily.tail(_MAX_DAILY_POINTS_RETURNED).items()
                ],
                "forecast": [
                    {"date": d.strftime("%Y-%m-%d"), "spend": round(float(v), 2)}
                    for d, v in zip(future_idx, daily_fc)
                ],
            },
            "monthly": {
                "history": [
                    {"month": d.strftime("%Y-%m"), "spend": round(float(v), 2)}
                    for d, v in monthly.items()
                ],
                "forecast": [
                    {"month": next_month_idx.strftime("%Y-%m"), "spend": round(month_fc, 2)}
                ],
            },
            "next_30_day_total": round(float(np.sum(daily_fc)), 2),
            "next_month_total": round(month_fc, 2),
            "accuracy": accuracy,
            "daily_accuracy": daily_accuracy,
            "message": (
                f"Forecast generated with {method} from {n_months} months "
                f"({n_days} days) of history."
            ),
        }
    except Exception as e:  # pragma: no cover - last-resort guard
        return {"success": False, "error": f"Forecast failed: {e}"}
