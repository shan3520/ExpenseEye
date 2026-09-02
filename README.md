# ExpenseEye - Personal Finance Analytics

> Privacy-first bank statement analyzer with intelligent subscription detection and overspending alerts

**Copyright © 2026 Shantanu (shan3520). All rights reserved.**  
**Original Author:** [Shantanu](https://github.com/shan3520)  
**Repository:** [github.com/shan3520/expenseeye](https://github.com/shan3520/expenseeye)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646cff.svg)](https://vite.dev/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.7-f7931e.svg)](https://scikit-learn.org/)
[![statsmodels](https://img.shields.io/badge/statsmodels-0.14-3f6ab5.svg)](https://www.statsmodels.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **🌐 Live demo:** [expenseeye.pages.dev](https://expenseeye.pages.dev) (frontend) · API at `https://smartspend-v975.onrender.com`
>
> No bank statement to hand? **"Try a sample statement"** on the landing page loads
> [`viewer/public/sample-statement.csv`](viewer/public/sample-statement.csv) and analyses it in one click —
> 8 months, 533 transactions, entirely synthetic. It is shaped like a real Indian bank
> export (banner preamble, `DD/MM/YY`, split Withdrawal/Deposit columns, trailing footer)
> so loading it exercises the auto-mapper, and it contains one genuinely missing
> subscription charge and one large one-off purchase so the exception list and the
> forecast's one-off handling have real work to show. Regenerate with
> `python scripts/make_sample_statement.py`.
> _First request after idle can take up to ~60s while the free-tier backend wakes from sleep; the app shows a waking state and waits it out._

## Overview

ExpenseEye is a privacy-conscious financial analytics platform that helps you understand your spending patterns. It is open-source and self-hostable; on the public demo your bank-statement CSV is parsed by ExpenseEye's own API (on infrastructure the operator controls) — session-scoped and auto-deleted — never sold or handed to a third-party data broker. Upload your CSV and get instant insights into recurring subscriptions, overspending months, and — powered by real machine learning — a cash-flow forecast, automatic transaction categorization, and anomaly detection.

**Key Features:**
- 🔒 **Privacy-conscious**: parsed by ExpenseEye's own API (self-hostable), session-scoped and auto-deleted — never sold or shared with data brokers
- 📊 **Smart CSV Auto-Mapper**: handles common real-world layouts — comma / semicolon / tab / pipe delimiters, ISO / DD-MM / MM-DD dates, DrCr+Amount, Debit/Credit and signed-amount columns, thousands separators (incl. European decimal commas), currency symbols and codes, and CR/DR markers. Ragged rows and implausible dates are skipped and reported, never silently dropped.
- 💳 **Subscription Detection**: Identifies recurring payments with confidence scores
- 📈 **Overspending Analysis**: Statistical detection of unusual spending months
- 🔮 **Cash-Flow Forecast (ML)**: Holt-Winters time-series forecast of the next 30 days / next month, with MAE/RMSE/MAPE accuracy reporting
- 🏷️ **Smart Categorization (ML)**: TF-IDF + LogisticRegression classifier labels each transaction, with a rule-based fallback for low-confidence cases
- 🚨 **Anomaly Detection (ML)**: Robust per-category z-scores flag unusual transactions with plain-English explanations
- 🌍 **Global Support**: Auto-detects DD/MM/YYYY and MM/DD/YYYY date formats
- ⚡ **Session-Based**: Ephemeral SQLite databases - data deleted after session
- 🖥️ **"Vault Terminal" UI**: themeable dark/light instrument console - a 2-column landing with a live board preview, a parse/classify boot sequence on upload, and terminal-style readouts and error alerts throughout (WCAG 2.1 AA, reduced-motion aware)

## Architecture

```
expenseeye/
├── api/              # Flask REST API backend
│   └── app.py        # API endpoints
├── core/             # Business logic modules
│   ├── loader.py         # CSV auto-mapper
│   ├── subscriptions.py  # Subscription detection (rule-based)
│   ├── overspending.py   # Overspending analysis (rule-based)
│   ├── forecast.py       # Cash-flow forecast (statsmodels Holt-Winters)
│   ├── categorizer.py    # ML transaction categorizer (TF-IDF + LogisticRegression)
│   └── anomaly.py        # Anomaly detection (robust z-score)
├── models/           # Persisted ML artifacts
│   ├── category_clf.joblib   # Trained categorizer (loaded once at startup)
│   └── model_card.json       # Held-out evaluation metrics
├── data/             # Seed + sample data (synthetic, safe to commit)
│   ├── seed_transactions.csv # Labeled training data for the categorizer
│   └── sample_statement.csv  # Realistic 18-month statement for demos
├── scripts/          # Reproducible data generation + model training
│   ├── generate_data.py
│   └── train_categorizer.py
├── viewer/           # React + Vite + Tailwind frontend
│   ├── src/          # Components, API client, types
│   └── package.json  # Frontend dependencies
├── render.yaml       # Render Blueprint for the API
└── requirements.txt  # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20.19+ or 22.12+ (the frontend uses Vite 8)
- pip and npm

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/shan3520/expenseeye.git
cd expenseeye
```

2. **Install backend dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the backend API**
```bash
python api/app.py
```

4. **Run the frontend (in a new terminal)**
```bash
cd viewer
npm install
npm run dev
```

5. **Access the application**
- Frontend: http://localhost:5173
- API: http://localhost:5000

> The frontend reads the API URL from the `VITE_API_URL` env var (defaults to `http://localhost:5000`). Create `viewer/.env` with `VITE_API_URL=...` to point at a deployed backend.

## Deployment

> **Live deployment:** API on **Render** (`https://smartspend-v975.onrender.com`),
> frontend on **Cloudflare Pages** (`https://expenseeye.pages.dev`). A
> [`render.yaml`](render.yaml) Blueprint is included.

### Backend (Render)

1. **Create a new Web Service** on [Render](https://render.com) (or use the included `render.yaml` Blueprint)
2. **Connect your GitHub repository**
3. **Configure the service:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:**
     ```
     gunicorn api.app:app --workers 1 --threads 4 --worker-class gthread --timeout 120 --graceful-timeout 30 --bind 0.0.0.0:$PORT --access-logfile -
     ```
   - **Environment:** Python 3.11+

   > `python api/app.py` still works and is what local development uses, but it
   > runs Werkzeug's **development** server, which says so on boot. gunicorn adds
   > request timeouts, worker supervision and graceful restarts.
   >
   > **Sizing is measured, not guessed.** A warmed worker holds ~168 MB (pandas +
   > statsmodels + scikit-learn) against the free plan's 512 MB on 0.1 CPU, so a
   > second worker would double memory while contending for the same CPU slice —
   > concurrency comes from threads instead. `--timeout 120` is not padding: the
   > default is 30s and `/forecast` alone measured 17s on a 25k-row statement, so
   > a large upload would be killed mid-request and surface as a 502.
   >
   > gunicorn does not run on Windows (it needs `fcntl`), which is why local
   > development keeps using `python api/app.py`.
4. **Set environment variable** `CORS_ORIGINS` to your frontend origin, e.g.
   `https://expenseeye.pages.dev` (comma-separated for multiple).

> ℹ️ The ML stack (scikit-learn, statsmodels, scipy) makes the first build
> slower and more memory-hungry than a plain Flask app. The trained model is
> committed under `models/`, so **no training happens at deploy time**.

### Frontend (Cloudflare Pages)

1. **Create a new Pages project** on [Cloudflare Pages](https://pages.cloudflare.com) and connect your GitHub repository.
2. **Configure the build:**
   - **Root directory:** `viewer`
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
3. **Add environment variable:**
   - `VITE_API_URL = https://your-render-app.onrender.com`
4. **Deploy.** On every push to `main`, Cloudflare rebuilds automatically.

> See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full step-by-step guide.

## Supported CSV Formats

ExpenseEye automatically detects and handles multiple CSV formats:

### Date Columns
- `Date`, `Transaction Date`, `Txn Date`, `Posting Date`, `Value Date`
- Supports: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD

### Description Columns
- `Description`, `Name`, `Narration`, `Merchant`, `Details`, `Particulars`, `Remarks`
- Optional - uses "TRANSACTION" placeholder if not found

### Amount Patterns

**Pattern 1: DrCr + Amount**
```csv
Date,Description,DrCr,Amount
01/01/2024,Netflix,DR,15.99
05/01/2024,Salary,CR,3000.00
```

**Pattern 2: Debit + Credit Columns**
```csv
Date,Description,Debit,Credit
01/01/2024,Netflix,15.99,
05/01/2024,Salary,,3000.00
```

**Pattern 3: Signed Amount**
```csv
Date,Description,Amount
01/01/2024,Netflix,-15.99
05/01/2024,Salary,3000.00
```

### Special Features
- ✅ Skips metadata header rows automatically
- ✅ Handles empty cells and whitespace
- ✅ Supports files up to 10MB
- ✅ Clear error messages showing detected vs expected columns

## API Documentation

### Endpoints

#### `POST /upload`
Upload a bank statement CSV file.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (CSV file)

**Response:**
```json
{
  "success": true,
  "session_id": "uuid-here",
  "message": "File processed successfully",
  "transactions_loaded": 265,
  "mapping_info": {
    "date_column": "Value Date",
    "description_column": "None (using TRANSACTION placeholder)",
    "amount_pattern": "Debit/Credit (Debit + Credit)",
    "rows_skipped": 167
  }
}
```

#### `GET /subscriptions?session_id=<uuid>`
Get detected subscriptions for a session.

**Response:**
```json
{
  "success": true,
  "subscriptions": [
    {
      "description": "Netflix",
      "amount": -15.99,
      "frequency": "MONTHLY",
      "avg_gap": 30,
      "occurrences": 12
    }
  ]
}
```

#### `GET /overspending?session_id=<uuid>`
Get overspending analysis for a session.

**Response:**
```json
{
  "success": true,
  "overspending": [
    {
      "month": "2024-03",
      "total_spending": 5000.0,
      "avg_spending": 3500.0,
      "pct_deviation": 42.86,
      "status": "OVERSPENDING"
    }
  ]
}
```

#### `GET /forecast?session_id=<uuid>`
Cash-flow forecast (ML). Forecasts the next 30 days and next month of spending
using Holt-Winters exponential smoothing, with a moving-average/linear-trend
baseline fallback for sparse history. Reports holdout accuracy.

**Response (abridged):**
```json
{
  "success": true,
  "method": "Holt-Winters (ExponentialSmoothing)",
  "history_months": 18,
  "next_30_day_total": 55345.89,
  "next_month_total": 66216.41,
  "accuracy": { "mae": 3274.09, "rmse": 3575.15, "mape": 5.21, "holdout_months": 4 },
  "monthly": { "history": [{ "month": "2023-01", "spend": 47000.0 }], "forecast": [{ "month": "2024-07", "spend": 66216.41 }] }
}
```

#### `GET /forecast?session_id=<uuid>`

Note: the analysis window is capped at the most recent 3 years and the returned
daily series at 400 points (`history_truncated` reports when this applies). A
statement carrying a mistyped year would otherwise build a continuous daily index
spanning centuries — 213k points and a ~7.7 MB response from a 3-row file.

#### `GET /reconcile`  (session id via `X-Session-Id`)

Reconciles the **expected** recurring ledger (detected series: merchant + cadence +
amount band) against the **actual** charges in the statement. Returns a match rate over
every expected occurrence plus a two-sided exception list — `missing` (expected charge
never landed) and `unscheduled` (recurring-merchant charge no occurrence explains).
Matched rows carry day-drift and amount-variance; a series that simply stopped is
reported as `lapsed` rather than generating phantom missing rows.

Monthly and quarterly schedules are projected by **calendar month** (same day of
month, clamped for short months), not by a fixed day count. A fixed count
accumulates about half a day of error per cycle, so on a multi-year statement the
projected date drifts outside the match tolerance and every later charge is
reported *both* as a missing occurrence and as an unscheduled charge. On a 75-month
series billed on the 3rd of every month that produced a 71.2% match rate with 21
missing and 23 unscheduled; the correct answer, now reported, is 100% with an empty
exception list.

#### `GET /categorize?session_id=<uuid>`
ML transaction categorization. Uses a trained TF-IDF + LogisticRegression
classifier, falling back to rule-based keyword matching only for low-confidence
predictions.

**Response (abridged):**
```json
{
  "success": true,
  "counts": { "total": 613, "model": 580, "rule_fallback": 33 },
  "breakdown": [{ "category": "rent", "total_spend": 396000.0 }],
  "transactions": [{ "description": "NETFLIX", "category": "subscriptions", "confidence": 0.94, "source": "model" }]
}
```

#### `GET /model-card`
Returns the categorizer's held-out evaluation metrics (no session required).

**Response (abridged):**
```json
{
  "success": true,
  "model": "TF-IDF (word 1-2gram + char 3-5gram) + LogisticRegression",
  "metrics": { "accuracy": 0.9314, "macro_precision": 0.9379, "macro_recall": 0.9301, "macro_f1": 0.9306 }
}
```

#### `GET /anomalies?session_id=<uuid>`
Statistical anomaly detection. Flags unusual transactions using robust
per-category z-scores (median + MAD) and explains why each was flagged.

**Response (abridged):**
```json
{
  "success": true,
  "method": "Robust per-category z-score (median + MAD)",
  "anomaly_count": 26,
  "anomalies": [{ "description": "ADOBE CREATIVE CLOUD", "category": "subscriptions", "z_score": 4.8, "explanation": "1811 is 3.2x the typical subscriptions spend (~564); robust z-score 4.8 exceeds 3.5." }]
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

## Analytics Algorithms

### Subscription Detection

**Algorithm:**
1. Group by a NORMALIZED description (card/reference digits stripped) and an
   amount BUCKET — within 15% or ₹50 of the group median — so a subscription
   whose price drifts with a GST revision or a plan change stays one series
2. Require minimum 3 occurrences in the amount band
3. Reject a series that is a lucky slice of a variable-spend merchant: it must
   either be most of what that merchant ever charged (≥50% coverage) **or** be
   effectively fixed-price (amount MAD ≤ 1% or ₹5). Either bar alone is unsafe —
   coverage rejects a real Prime subscription buried in Amazon orders, and
   fixed-price rejects a real subscription after a price rise
4. Take day gaps between consecutive charges; cadence comes from the MEDIAN gap,
   so one skipped or early-billed month does not disqualify the series
5. Classify as WEEKLY (6–8 days), FORTNIGHTLY (12–16), MONTHLY (25–35) or
   QUARTERLY (84–100). Longer cadences demand more evidence: QUARTERLY needs 4
   occurrences (a full year), MONTHLY needs 3
6. Require regularity on BOTH a proportional and an absolute bound — gap MAD ≤
   min(40% of the median gap, 7 days). The proportional bound alone allows ±36
   days of drift on a quarterly series, which lets irregular repeat purchases
   pass as a subscription

Detection is a pure read — it never writes to the database.

### Overspending Detection

**Algorithm:**
1. Calculate monthly spending totals
2. For each month (after a 3-month baseline):
   - Calculate the average and standard deviation of **every prior month**
   - Flag if spending > 120% of average **OR** > avg + 2σ
3. Report percentage deviation and the z-score

The two arms catch different failures: the percentage arm catches a steady
drift upward that never breaks 2σ on noisy data, and the sigma arm catches a
genuine spike on a month whose baseline is unusually low. Requiring both
conditions together missed each of those cases.

**Statistical Approach:**
- No data leakage: only uses months strictly before the one being judged
- Handles zero/undefined variance with a 10% floor on std_dev
- Skips the first 3 months (insufficient history)

### Anomaly Detection (ML)

**Method:** robust per-category z-score (median + MAD), so a handful of extreme
outliers cannot inflate the spread and mask each other.

Two things are deliberately **not** flagged:

- **Detected subscriptions.** A predictable monthly charge is a subscription,
  not an unexplained outlier. They stay in the population (dropping them would
  gut the statistics on subscription-heavy statements) but are excluded from
  candidacy.
- **Charges that are ordinary for their own merchant.** A category is a coarse
  bucket: petrol (₹900–2,600) shares `transport` with bike taxis (₹45–190), so
  *every* fill scores a huge category z-score. On the demo statement that
  flagged 28 charges of which **27 were the same petrol station** — and
  something that happens 27 times is a pattern, not an anomaly. A charge must
  now be unusual for its category **and** for its merchant.

The merchant test is not an amnesty. It applies only to merchants seen at least
4 times, so a genuine one-off from a first-time merchant is still flagged; and a
merchant you use constantly can still make one charge that does not belong — a
₹84,999 purchase at a merchant whose usual is ₹1,800 is flagged, with the
merchant comparison stated in the explanation. Suppressed charges are counted in
`routine_for_merchant_suppressed`, so "found nothing" and "ruled these out" stay
distinguishable.

  demo statement:  28 flagged -> 1 flagged, 27 reported as routine-for-merchant

### Cash-Flow Forecast (ML)

**Model:** Holt-Winters exponential smoothing (`statsmodels`) on a daily and
monthly spend time series, with a moving-average + linear-trend baseline
fallback when history is sparse (< ~60 daily points or < 6 months). Never
crashes on sparse data.

**One-off charges are excluded from what the model learns.** A laptop, a
deposit, an annual premium is real money but is not a recurring pattern to
project; left in, the trend chases it and the model predicts another one. On a
six-month statement, one ₹84,999 purchase moved next-month from ₹65,830 to
₹94,163 and MAPE from 12.7% to 102%.

A charge qualifies only if it is (1) not part of a detected recurring series,
(2) large against the statement (robust z on median + MAD), and (3) **≥20% of
its own month** — the test that separates *large* from *distorting*. Rent fails
(1); a ₹2,651 shopping trip in a ₹70,000 month fails (3).

Damping is then a **hypothesis that must win a back-test**, not an assumption.
Both candidate models are graded against the same target — the raw totals
actually spent — and the damped one is used only if it predicts those totals
better. This is not decoration: on `sample_statement.csv`, whose rent is written
inconsistently (`LANDLORD RENT` / `HOUSE RENT TRANSFER`), the detector wrongly
called 18 rent payments one-offs; the back-test caught it (MAE ₹3,274 → ₹25,004)
and the raw model was kept. Nothing is hidden either way: the charges are named
in the response, the spike stays in the charted history, they remain flagged
under Anomalies, and the rejected candidate's accuracy is published beside the
chosen one.

**Both headline totals come from one model.** `next_30_day_total` used to be the
sum of an independent *daily* model while `next_month_total` came from the
*monthly* one, so the two figures were different forecasts and openly
contradicted each other on screen (₹1,02,366 beside ₹69,594 — a 47% gap). The
30-day figure is now the month forecast scaled by `30 / days-in-month`.

**Accuracy — reported on two datasets, each labelled (these metrics are dataset-dependent):**
- **Synthetic sample** (`data/sample_statement.csv`): monthly rolling one-step-ahead
  holdout **MAE ₹3,274 · RMSE ₹3,575 · MAPE 5.21%**. Holt-Winters fits this generator
  (a linear trend + seasonality) almost by construction, so this characterises the
  data, not real-world skill.
- **Real statement** (a 22-month bank export, removed from the repo for privacy — see
  P1-11): **MAE ₹22,527 · RMSE ₹30,561 · MAPE 36.72%** — the honest real-world figure.
  (It measured ~142% before the ISO-8601 date bug was fixed; correcting the timeline
  brought it down, and it does not approach the synthetic 5%.)
- Daily MAE/RMSE is a secondary metric (per-day MAPE is unreliable on spiky transaction
  data, so the monthly aggregate is the headline). A statement too short to back-test
  returns `accuracy: null`, and the UI says so explicitly rather than showing a blank.

### Transaction Categorizer (ML)

**Model:** TF-IDF features over **word (1-2 gram)** and **character (3-5 gram)**
n-grams → **LogisticRegression**, persisted to `models/category_clf.joblib` and
loaded once at startup. Low-confidence predictions fall back to keyword rules.

**Accuracy — reported on two datasets, each labelled:**
- **Synthetic seed holdout** (25% stratified, 9 categories): **Accuracy 93.1% · Macro-F1
  93.1%**. This holdout shares its merchant vocabulary with training, so it largely
  measures **memorisation, not generalisation**.
- **Held-out realistic set** (`data/eval_transactions.csv`, 40 hand-labelled Indian
  merchants; model-only, independent of the keyword fallback): **argmax accuracy 77.5% ·
  confident-coverage 70% · accuracy-when-confident 89.3%**. Below the confidence
  threshold the pipeline falls back to keyword rules. This curated set is *indicative*;
  a larger **owner-supplied real labelled set** is the definitive generalisation measure
  (owner-gated, P1-5).
- The keyword fallback now covers common Indian merchants (quick-commerce, fintech,
  ride-hailing, streaming); the `jio` rule bug that mislabelled JIOMART as *utilities*
  is fixed.

Retrain anytime: `python scripts/generate_data.py && python scripts/train_categorizer.py`

### Anomaly Detection (ML)

**Method:** Robust per-category z-score using the **median + MAD** (Median
Absolute Deviation), so a few extreme outliers don't inflate the spread.
Transactions above a z-score of 3.5 are flagged with a plain-English
explanation of how far above the category norm they sit.

## Development

### Project Structure

```
expenseeye/
├── api/
│   └── app.py                 # Flask API with session management + CORS
├── core/
│   ├── loader.py              # CSV auto-mapper with smart detection
│   ├── subscriptions.py       # Subscription detection algorithm
│   ├── overspending.py        # Overspending analysis algorithm
│   ├── forecast.py            # Cash-flow forecast (Holt-Winters / baseline)
│   ├── categorizer.py         # ML categorizer (TF-IDF + LogisticRegression)
│   └── anomaly.py             # Anomaly detection (robust z-score)
├── models/                    # Trained model + model card (versioned)
├── data/                      # Synthetic seed + sample data (versioned)
├── scripts/                   # generate_data.py, train_categorizer.py
├── viewer/
│   ├── src/
│   │   ├── App.tsx            # Root React component
│   │   ├── components/        # FileUpload, SubscriptionsTable, OverspendingAnalysis,
│   │   │                      #   CashFlowForecast, TransactionCategories, AnomalyDetection
│   │   ├── lib/               # axios API client + utils
│   │   └── types/             # TypeScript interfaces
│   ├── package.json           # Frontend dependencies
│   └── vite.config.ts         # Vite config (@ alias → src)
├── render.yaml                # Render Blueprint for the API
├── requirements.txt           # Backend dependencies (incl. scikit-learn, statsmodels)
├── .gitignore                 # Excludes test files and sensitive data
└── README.md                  # This file
```

### Running Tests

```bash
# Test CSV auto-mapper with various formats
python test_csv_formats.py

# Diagnose a specific CSV file
python diagnose_csv.py your_file.csv
```

### Adding Support for New CSV Formats

1. **Add column aliases** in `core/loader.py`:
   ```python
   # In detect_date_column()
   aliases = ['date', 'transaction_date', 'your_new_alias']
   ```

2. **Test with sample CSV**:
   ```bash
   python diagnose_csv.py sample.csv
   ```

3. **Add to test suite** in `test_csv_formats.py`

## Security & Privacy

- **Self-hostable**: run the whole stack yourself so nothing leaves your machine. On the public demo, your statement is parsed by ExpenseEye's own API (on infrastructure the operator controls), not a third-party processor.
- **Session-based storage**: each upload gets an isolated SQLite database in the server's temp directory, keyed by an unguessable session UUID
- **Automatic cleanup**: session databases are deleted on exit (`DELETE /session/<id>`) and swept by a TTL reaper (default 30 min) — no manual cleanup needed
- **Minimal retention**: nothing persists beyond the session TTL; no accounts, analytics, or profiles are kept
- **File size limits**: 10MB maximum upload size
- **Input validation**: UUID-validated session paths, strict CSV parsing, and a per-IP rate limit on the upload/compute endpoints

## Troubleshooting

### CSV Upload Fails

**Error:** "Could not identify date column"
- **Solution:** Check if your CSV has a date column with one of the supported names
- **Debug:** Run `python diagnose_csv.py your_file.csv` to see detected columns

**Error:** "No valid transactions found"
- **Solution:** Verify your CSV has numeric values in amount columns
- **Debug:** Check for whitespace or special characters in amount cells

### Analytics Not Showing

**Subscriptions:** Requires minimum 3 occurrences of same amount
**Overspending:** Requires minimum 4 months of data (3-month baseline + 1 to analyze)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/) and [React](https://react.dev/) + [Vite](https://vite.dev/)
- CSV parsing powered by [pandas](https://pandas.pydata.org/)
- Deployed on [Render](https://render.com) (API) and [Cloudflare Pages](https://pages.cloudflare.com) (frontend)

## Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/shan3520/expenseeye/issues)
- Check existing documentation in `/docs`

---

**Made for privacy-conscious individuals who want to understand their spending without compromising their data.**
