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

from core.subscriptions import detect_subscriptions, normalize_description

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

# One-off charges -- a laptop, a deposit, an annual premium -- are real money but
# are not part of the recurring rhythm this forecast projects. Left in, a single
# such charge drags the trend up and the model predicts another one: on a real
# six-month statement one 84,999 purchase moved next-month from 65,830 to 94,163
# and MAPE from 12.7% to 102%. They are excluded from what the model LEARNS,
# never hidden: they stay in the charted history, they are counted and totalled
# in the response, and accuracy is reported both ways.
#
# A charge qualifies only if ALL THREE hold:
#   * it is not part of a detected recurring series -- rent IS the rhythm being
#     projected, and a size-only test flags it every month;
#   * it is large against the statement (robust z on median + MAD);
#   * it is material to its own month. That is the actual question. 84,999 in a
#     158,120 month is 54% and distorts everything; a 2,651 shopping trip in a
#     70,000 month is 3.8% and distorts nothing, however large it looks.
#
# The test is deliberately different from the per-category one the Anomalies
# module uses: that asks "is this unusual for its category", this asks "is this
# big enough to distort a monthly total". The lists agree on extremes and need
# not agree everywhere.
_ONEOFF_Z = 3.5
_MAD_SCALE = 1.4826              # MAD -> std-dev consistency for normal data
_MIN_ONEOFF_SAMPLE = 20          # too few rows to call anything an outlier
_MIN_MONTH_SHARE = 0.20          # must be >=20% of its month to count as distorting
_MAX_ONEOFF_FRACTION = 0.05      # safety valve: never damp more than 5% of rows


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


def _one_off_mask(df, db_path):
    """
    Boolean mask of charges large enough to distort a monthly total.

    Robust statistics (median + MAD) so the outliers being detected do not
    inflate the spread and mask each other. Returns an all-False mask when the
    statement is too small to judge, when spread is degenerate, or when the rule
    would flag an implausible share of the rows -- a statement of uniformly large
    transfers must not come back as 5% one-offs.
    """
    spend = df["spend"].to_numpy(dtype=float)
    none = np.zeros(len(spend), dtype=bool)
    if len(spend) < _MIN_ONEOFF_SAMPLE:
        return none

    med = float(np.median(spend))
    mad = float(np.median(np.abs(spend - med)))
    if mad <= 0:
        return none
    big = ((spend - med) / (_MAD_SCALE * mad)) > _ONEOFF_Z

    # Share of its own month -- the test that separates "large" from "distorting".
    month_total = (
        df.groupby(df["txn_date"].dt.to_period("M"))["spend"]
          .transform("sum")
          .to_numpy(dtype=float)
    )
    material = np.divide(
        spend, month_total, out=np.zeros_like(spend), where=month_total > 0
    ) >= _MIN_MONTH_SHARE

    # Never damp a recurring charge: it is the pattern being forecast, not noise.
    try:
        recurring = {normalize_description(x["description"]) for x in detect_subscriptions(db_path)}
    except Exception:                            # detection is best-effort here
        recurring = set()
    is_recurring = (
        df["description"].map(normalize_description).isin(recurring).to_numpy()
        if recurring else np.zeros(len(spend), dtype=bool)
    )

    mask = big & material & ~is_recurring
    if mask.sum() > max(1, int(_MAX_ONEOFF_FRACTION * len(spend))):
        return none
    return mask


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


def _monthly_holdout_accuracy(monthly, rich, eval_series=None):
    """
    Rolling one-step-ahead accuracy on the most recent months.

    Holds out the last k months; for each, trains on all prior months and
    forecasts one month ahead. Returns MAE/RMSE/MAPE on monthly totals, which
    is the meaningful accuracy for a cash-flow forecast.

    `eval_series` lets a model TRAINED on one series be GRADED against another --
    specifically, a one-off-damped model graded against the raw totals the user
    actually spent. Without that the two candidate models would be scored against
    different targets and could not be compared at all.
    """
    vals = monthly.values.astype(float)
    truth = vals if eval_series is None else eval_series.values.astype(float)
    n = len(vals)
    if n < 6 or len(truth) != n:
        return None
    k = min(6, max(2, n // 4))
    actual, pred = [], []
    for i in range(n - k, n):
        forecast = _forecast_one_month(vals[:i], rich)
        actual.append(truth[i])
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

        # Split the statement into the recurring baseline the model learns from
        # and the one-off charges that would otherwise drag the trend (see the
        # constants above). Both are kept: the charted history stays ACTUAL.
        one_off = _one_off_mask(df, db_path)
        df_base = df[~one_off]
        one_off_rows = df[one_off]
        if df_base.empty:                       # everything looked like an outlier
            df_base, one_off_rows = df, df.iloc[0:0]

        monthly_actual = _monthly_series(df)
        # Reindex onto the actual calendar so a month made up only of one-offs
        # becomes a zero-spend month rather than vanishing from the series.
        monthly = _monthly_series(df_base).reindex(monthly_actual.index, fill_value=0.0)
        daily_actual = _daily_series(df)
        daily = _daily_series(df_base).reindex(daily_actual.index, fill_value=0.0)

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
        # Damping one-offs is a HYPOTHESIS, not an article of faith, so it has to
        # earn its place on held-out months. Both candidates are graded against
        # the same target -- the raw totals actually spent -- so the comparison
        # is real, and the damped model is used only if it predicts those totals
        # better. This is what stops the rule misfiring: on a statement whose
        # rent is written inconsistently ("LANDLORD RENT" / "HOUSE RENT
        # TRANSFER") the detector wrongly called 18 rent payments one-offs, and
        # the back-test caught it -- MAE got worse, so the raw model is kept.
        acc_damped = _monthly_holdout_accuracy(monthly, rich, eval_series=monthly_actual)
        acc_raw = _monthly_holdout_accuracy(monthly_actual, rich)

        use_damped = bool(
            len(one_off_rows)
            and acc_damped and acc_raw
            and acc_damped["mae"] < acc_raw["mae"]
        )
        if not use_damped:
            monthly, daily = monthly_actual, daily_actual
            one_off_rows = df.iloc[0:0]
            n_days, n_months = int(len(daily)), int(len(monthly))

        accuracy = acc_damped if use_damped else acc_raw
        if accuracy:
            accuracy["basis"] = (
                "monthly totals, rolling one-step-ahead holdout"
                + (
                    f" ({len(one_off_rows)} one-off charge"
                    f"{'s' if len(one_off_rows) != 1 else ''} excluded from training)"
                    if use_damped else ""
                )
            )

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

        # "Next 30 days" is derived from the SAME monthly model as "next month",
        # scaled by month length. It used to be the sum of the independent daily
        # model, so the two headline figures were two different forecasts and
        # openly contradicted each other on screen -- 1,02,366 beside 69,594, a
        # 47% gap, with nothing to explain it. One model, one answer, and the
        # relationship between the two numbers is now arithmetic.
        days_in_next_month = int(next_month_idx.days_in_month)
        next_30_day_total = month_fc * (_DAILY_HORIZON / days_in_next_month)

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
                    for d, v in daily_actual.tail(_MAX_DAILY_POINTS_RETURNED).items()
                ],
                "forecast": [
                    {"date": d.strftime("%Y-%m-%d"), "spend": round(float(v), 2)}
                    for d, v in zip(future_idx, daily_fc)
                ],
            },
            "monthly": {
                # Actual spend, one-offs included: the spike is real and the
                # user must see it. Only what the MODEL LEARNS is damped.
                "history": [
                    {"month": d.strftime("%Y-%m"), "spend": round(float(v), 2)}
                    for d, v in monthly_actual.items()
                ],
                "forecast": [
                    {"month": next_month_idx.strftime("%Y-%m"), "spend": round(month_fc, 2)}
                ],
            },
            "next_30_day_total": round(next_30_day_total, 2),
            "next_month_total": round(month_fc, 2),
            "totals_basis": (
                f"both from the monthly model; 30-day figure is the month "
                f"forecast scaled by 30/{days_in_next_month}"
            ),
            "one_offs": {
                "count": int(len(one_off_rows)),
                "total": round(float(one_off_rows["spend"].sum()), 2),
                "charges": [
                    {
                        "date": r.txn_date.strftime("%Y-%m-%d"),
                        "description": str(r.description),
                        "amount": round(float(r.spend), 2),
                    }
                    for r in one_off_rows.sort_values("spend", ascending=False)
                                         .head(5).itertuples()
                ],
            },
            "accuracy": accuracy,
            # The candidate that was not used, kept visible so the choice above
            # can be checked rather than taken on trust.
            "accuracy_alternative": (acc_raw if use_damped else acc_damped),
            "one_offs_excluded_from_training": use_damped,
            "daily_accuracy": daily_accuracy,
            "message": (
                f"Forecast generated with {method} from {n_months} months "
                f"({n_days} days) of history."
            ),
        }
    except Exception as e:  # pragma: no cover - last-resort guard
        return {"success": False, "error": f"Forecast failed: {e}"}
