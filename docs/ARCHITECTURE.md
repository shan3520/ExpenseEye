# ExpenseEye Architecture

## System Overview

ExpenseEye follows a **three-tier architecture** with clear separation of concerns.

`core/` holds six read-out modules. Five analyse the statement independently;
**`reconcile.py` closes the loop over them** — it consumes the recurring series
found by `subscriptions.py`, projects when each charge should have landed, and
matches that expected ledger against what the statement actually contains. That
is what turns a set of read-outs into a finance-ops loop with a measurable match
rate and an exception list.

Dependencies flow one way (`api` → `core` → SQLite); no core module imports the
API, and modules that must agree share one implementation rather than
duplicating logic — `anomaly.py` categorizes through `categorizer.py`, and both
`reconcile.py` and `forecast.py` read recurring series from `subscriptions.py`.
Two independent copies of "what category is this?" had already drifted far
enough to label the same charge differently in two cards on the same screen.

```
┌─────────────────────────────────────────────────────────────┐
│                React Frontend (Vite + Tailwind)             │
│                       (viewer/src)                          │
│  - File upload UI                                           │
│  - Analytics visualization                                  │
│  - Session management                                       │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST (axios, CORS-enabled)
                     │
┌────────────────────▼────────────────────────────────────────┐
│                      Flask REST API                         │
│                     (api/app.py)                            │
│  - CSV upload endpoint                                      │
│  - Analytics endpoints                                      │
│  - Session-based routing                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │
┌────────────────────▼────────────────────────────────────────┐
│                    Core Business Logic                      │
│                      (core/*.py)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   loader.py  │  │subscriptions │  │overspending  │     │
│  │ CSV Auto-    │  │     .py      │  │     .py      │     │
│  │ Mapper       │  │ Subscription │  │ Overspending │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ forecast.py  │  │categorizer.py│  │  anomaly.py  │     │
│  │ Holt-Winters │  │ TF-IDF + LR  │  │ Robust       │     │
│  │ forecast (ML)│  │ classifier(ML)│  │ z-score (ML) │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│  ┌──────▼───────────────────────────────────▼───────┐     │
│  │                  reconcile.py                     │     │
│  │  Expected recurring ledger vs actual charges:     │     │
│  │  match rate + two-sided exception list            │     │
│  └───────────────────────────────────────────────────┘     │
│                    models/category_clf.joblib (loaded once)│
└────────────────────┬────────────────────────────────────────┘
                     │
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 SQLite Database (Ephemeral)                 │
│              <tempdir>/expenseeye_{uuid}.db                 │
│  - transactions table                                       │
│  - Session-scoped                                           │
│  - Auto-cleanup                                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer (React)

**Location:** `viewer/src` (entry: `App.tsx`)

**Responsibilities:**
- User interface for CSV upload
- Display analytics results
- Session state management
- Error handling and user feedback

**Key Features:**
- File upload with drag-and-drop, and a terminal-style `[SYS_ERR]` alert on failure
- Two-column landing (hero + decorative console preview) and an open-source / privacy trust section
- A ~2.5s "boot sequence" hand-off on successful upload, then the analytics dashboard
- Themeable dark/light "Vault Terminal" UI; responsive; reduced-motion aware

**Technology Stack:**
- React 19 + TypeScript
- Vite 8 (build/dev server)
- Tailwind CSS
- axios (HTTP client)

### 2. API Layer (Flask)

**File:** `api/app.py`

**Responsibilities:**
- RESTful API endpoints
- Request validation
- Session management
- Error handling

**Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/upload` | Upload CSV and create session |
| GET | `/subscriptions?session_id=<uuid>` | Get subscription analysis |
| GET | `/overspending?session_id=<uuid>` | Get overspending analysis |
| GET | `/forecast?session_id=<uuid>` | Cash-flow forecast (ML) |
| GET | `/categorize?session_id=<uuid>` | Transaction categorization (ML) |
| GET | `/model-card` | Categorizer evaluation metrics (ML) |
| GET | `/anomalies?session_id=<uuid>` | Anomaly detection (ML) |
| GET | `/health` | Health check |

**Session Management:**
- UUID-based session IDs
- Isolated SQLite databases per session
- Temporary file storage
- Automatic cleanup

**Technology Stack:**
- Flask 3.0+
- Werkzeug (file handling)
- UUID (session IDs)

### 3. Business Logic Layer

#### 3.1 CSV Auto-Mapper (`core/loader.py`)

**Purpose:** Intelligently parse diverse bank CSV formats

**Key Functions:**

```python
find_header_row(csv_path)
# Detects actual header row, skipping metadata

detect_date_column(columns)
# Identifies date column from 10+ aliases

detect_description_column(columns, df=None, exclude=None)
# Identifies description column; falls back to content heuristic
# (text-heavy column) when header aliases miss

detect_amount_pattern(columns)
# Detects: DrCr, Debit/Credit, or Signed Amount

detect_date_format(df, date_col)
# Auto-detects DD/MM/YYYY vs MM/DD/YYYY

coerce_amount(value)
# Cleans thousands separators, currency symbols, CR/DR markers and
# parentheses negatives before float conversion

normalize_amount(row, pattern, *cols)
# Converts various amount formats to float (via coerce_amount)

load_csv_to_db(csv_path, db_path)
# Main orchestration function
```

**Algorithm Flow:**

```
1. Find header row (skip metadata)
2. Read CSV with detected header
3. Detect date column
4. Detect description column (optional)
5. Detect amount pattern
6. Auto-detect date format
7. Create SQLite database
8. For each row:
   a. Parse date with detected format
   b. Get description (or use placeholder)
   c. Calculate amount based on pattern
   d. Insert into database
9. Return transaction count + mapping info
```

**Supported Formats:**

| Pattern | Columns | Example |
|---------|---------|---------|
| DrCr | DrCr, Amount | `DR, 100.00` |
| Debit/Credit | Debit, Credit | `100.00, ` or `, 100.00` |
| Signed Amount | Amount | `-100.00` or `100.00` |

#### 3.2 Subscription Detection (`core/subscriptions.py`)

**Purpose:** Identify recurring payments automatically

**Algorithm:**

```
1. Group transactions by (description, amount)
2. Filter: amount < 0 (debits only)
3. Require: minimum 3 occurrences
4. Calculate day gaps between consecutive transactions
5. Compute: average gap, std deviation
6. Classify frequency:
   - MONTHLY: 25-35 days average
   - WEEKLY: 5-9 days average
7. Validate consistency: std_dev < 20% of avg_gap
8. Return subscriptions with confidence scores
```

**Output Schema:**

```python
{
    "description": str,      # Transaction description
    "amount": float,         # Negative amount
    "frequency": str,        # "MONTHLY" or "WEEKLY"
    "avg_gap": float,        # Average days between payments
    "occurrences": int       # Number of times detected
}
```

**Example:**
```python
{
    "description": "Netflix",
    "amount": -15.99,
    "frequency": "MONTHLY",
    "avg_gap": 30.2,
    "occurrences": 12
}
```

#### 3.3 Overspending Analysis (`core/overspending.py`)

**Purpose:** Detect months with unusual spending

**Algorithm:**

```
1. Aggregate spending by month
2. For each month (after 3-month baseline):
   a. Calculate historical average (previous months only)
   b. Calculate historical std deviation
   c. Handle edge case: std_dev = max(actual_std, avg * 0.1)
   d. Define thresholds:
      - Threshold 1: avg * 1.2 (20% above average)
      - Threshold 2: avg + std_dev (statistical outlier)
   e. Flag if spending > either threshold
   f. Calculate percentage deviation
3. Return flagged months with statistics
```

**Statistical Approach:**
- **No data leakage**: Only uses historical data
- **Adaptive baseline**: Recalculates for each month
- **Robust to variance**: Minimum 10% std deviation

**Output Schema:**

```python
{
    "month": str,                # "YYYY-MM"
    "total_spending": float,     # Total spent in month
    "avg_spending": float,       # Historical average
    "pct_deviation": float,      # Percentage above average
    "status": str                # "OVERSPENDING" or "NORMAL"
}
```

#### 3.4 Cash-Flow Forecast (`core/forecast.py`) — ML

**Purpose:** Forecast upcoming spending from the transaction history.

**Approach:**
```
1. Aggregate expenses into daily + monthly spend series (gaps filled with 0)
2. If history is rich (>= ~60 daily points AND >= 6 months):
     fit statsmodels Holt-Winters ExponentialSmoothing
       - daily:   additive trend + weekly (period 7) seasonality
       - monthly: trend (+ yearly seasonality when >= 24 months)
   else: moving-average + linear-trend baseline (never crashes)
3. Back-test on a held-out slice -> MAE / RMSE / MAPE
     - headline accuracy is MONTHLY (rolling one-step-ahead); per-day MAPE on
       spiky data is unreliable, so it is reported only as a secondary metric
```

**Libraries:** `statsmodels`, `numpy`, `pandas`.

#### 3.5 Transaction Categorizer (`core/categorizer.py`) — ML

**Purpose:** Replace rule-based labels with a trained text classifier.

**Approach:**
```
Features: FeatureUnion(
            TF-IDF word  n-grams (1-2),
            TF-IDF char  n-grams (3-5)   # robust to bank abbreviations
          )
Model:    LogisticRegression (calibrated probabilities)
Persist:  models/category_clf.joblib  (trained once, loaded at startup)
Fallback: keyword rules for predictions below the confidence threshold (0.45)
```

Training + evaluation live in `scripts/train_categorizer.py`; metrics are
written to `models/model_card.json` and surfaced via `/model-card`.

**Libraries:** `scikit-learn`, `joblib`.

#### 3.6 Anomaly Detection (`core/anomaly.py`) — ML

**Purpose:** Replace the fixed overspending threshold with a statistical method.

**Approach:**
```
For each spend category:
  median + MAD (Median Absolute Deviation, robust to outliers)
  z = (spend - median) / (1.4826 * MAD)
  flag transactions with z >= 3.5, with a human-readable explanation
```

Two exclusions from **candidacy** (both stay in the population, because removing
them would distort the statistics used to judge everything else):

- **Detected subscriptions** — a predictable monthly charge is a subscription,
  not an unexplained outlier.
- **Charges that are routine for their own merchant** — a category is a coarse
  bucket, so petrol scores a huge `transport` z-score on *every* fill. Requires
  ≥4 sightings of that merchant, so a first-time merchant cannot excuse itself.

**Libraries:** `numpy`, `pandas`. Categories come from `categorizer.py` via the
shared `predict_categories()` — not a second copy of the logic, which had
previously drifted far enough to label one charge differently in two cards.

#### 3.7 Recurring Reconciliation (`core/reconcile.py`)

**Purpose:** Close the loop. Everything above *describes* a statement; this
module makes a claim and then checks it.

**Approach:**
```
for each recurring series from subscriptions.py:
    project expected occurrences across the OBSERVED life of the series
      - MONTHLY/QUARTERLY step by CALENDAR month (same day-of-month),
        not a fixed day count
    greedy nearest-match each expected date against actual charges
      - date tolerance : 35% of cadence, clamped to 3-10 days
      - amount tolerance: 15% or ₹50, whichever is larger
    anything unmatched on either side becomes an exception
```

**Output:** a match rate over every expected occurrence, plus a two-sided
exception list — `missing` (expected but never landed) and `unscheduled` (a
charge from a recurring merchant that no occurrence explains).

**Invariant:** `matched + missing == expected_occurrences`, enforced by a test.
Nothing is quietly dropped to make the rate look better.

**Why calendar months:** a fixed day count accumulates ~half a day of error per
cycle. Past ~20 cycles the projection drifts outside tolerance and every real
charge is counted *both* as missing and as unscheduled — a fake match rate with
both sides of the exception list corrupted at once. It is invisible on a
six-month statement, which is why two QA rounds missed it.

**Libraries:** `pandas`, `calendar`.

### 4. Data Layer (SQLite)

**Database Schema:**

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_date DATE,
    description TEXT,
    amount REAL
);
```

**Session Isolation:**
- Each upload creates a new database: `/tmp/ExpenseEye_{uuid}.db`
- No cross-session data access
- Automatic cleanup on session end

**Indexing:**
- Primary key on `id`
- Implicit index on `txn_date` (via ORDER BY queries)

## Data Flow

### Upload Flow

```
User uploads CSV
    ↓
React frontend sends to /upload
    ↓
Flask validates file
    ↓
Generate session UUID
    ↓
Create temp database: /tmp/ExpenseEye_{uuid}.db
    ↓
Call load_csv_to_db()
    ↓
    ├─ Find header row
    ├─ Detect columns
    ├─ Detect date format
    ├─ Parse each row
    └─ Insert into database
    ↓
Return session_id + mapping_info
    ↓
React frontend stores session_id
    ↓
Play the Processing terminal boot sequence (~2.5s), then reveal the dashboard
```

### Analytics Flow

```
User clicks "Detect Subscriptions"
    ↓
React frontend calls /subscriptions?session_id={uuid}
    ↓
Flask retrieves session database
    ↓
Call detect_subscriptions(db_path)
    ↓
    ├─ Query all debit transactions
    ├─ Group by (description, amount)
    ├─ Calculate day gaps
    ├─ Classify frequency
    └─ Filter by consistency
    ↓
Return subscription list
    ↓
React frontend displays results
```

## Design Decisions

### 1. Session-Based Architecture

**Why:** Privacy and scalability
- No persistent user data
- Horizontal scaling possible
- Automatic cleanup

**Trade-offs:**
- ✅ Privacy-first
- ✅ Stateless API
- ❌ No historical comparison across uploads

### 2. SQLite for Storage

**Why:** Simplicity and portability
- No external database needed
- File-based isolation
- ACID transactions

**Trade-offs:**
- ✅ Zero configuration
- ✅ Perfect for session scope
- ❌ Not suitable for concurrent writes (not needed)

### 3. Auto-Detection vs Configuration

**Why:** User experience
- No manual column mapping
- Works with 20+ bank formats
- Reduces friction

**Trade-offs:**
- ✅ Seamless user experience
- ✅ Handles most formats
- ❌ May fail on very unusual formats

### 4. Statistical Overspending Detection

**Why:** Adaptive to user's spending patterns
- No hardcoded thresholds
- Accounts for variance
- Learns from history

**Trade-offs:**
- ✅ Personalized to each user
- ✅ Statistically sound
- ❌ Requires 4+ months of data

## Security Considerations

### 1. Input Validation
- File size limit: 10MB
- File type validation: CSV only
- SQL injection prevention: Parameterized queries

### 2. Session Security
- UUID v4 for session IDs (cryptographically random)
- No session data in URLs (except session_id)
- Temporary file cleanup

### 3. Data Privacy
- No persistent storage
- No external API calls
- No data logging
- Ephemeral databases

### 4. Error Handling
- No sensitive data in error messages
- Generic errors for security issues
- Detailed errors only for user mistakes

## Performance Characteristics

### CSV Upload
- **Time Complexity:** O(n) where n = number of rows
- **Space Complexity:** O(n) for in-memory DataFrame
- **Bottleneck:** pandas CSV parsing
- **Optimization:** Streaming parser for very large files (future)

### Subscription Detection
- **Time Complexity:** O(n log n) due to grouping and sorting
- **Space Complexity:** O(n) for transaction storage
- **Bottleneck:** Date parsing and grouping
- **Optimization:** Already efficient for typical datasets

### Overspending Analysis
- **Time Complexity:** O(m) where m = number of months
- **Space Complexity:** O(m) for monthly aggregates
- **Bottleneck:** Monthly aggregation
- **Optimization:** Already efficient

### Scalability
- **Concurrent Users:** Limited by Flask (use Gunicorn in production)
- **File Size:** Limited to 10MB (configurable)
- **Transaction Count:** Tested up to 10,000 transactions
- **Database Size:** Typical 1-2MB per session

## Future Enhancements

### Delivered (v3.0.0)
- ✅ **Recurring reconciliation** — match rate + two-sided exception list
- ✅ Split-narration recombination (rail column + counterparty column)
- ✅ One-off charges excluded from forecast training, gated on a back-test
- ✅ Merchant-level anomaly suppression (a pattern is not an anomaly)
- ✅ One-click sample statement on the landing page
- ✅ Session survives a page refresh; served by gunicorn; deploys from CI

### Delivered (v2.0.0)
- ✅ Currency symbol handling (₹, $, €)
- ✅ Thousand separator support (1,000.00) + CR/DR markers
- ✅ Spending category classification (ML categorizer)
- ✅ Anomaly detection (robust per-category z-score)
- ✅ Cash-flow forecasting (Holt-Winters)

### Short Term
1. Support for Excel files directly
2. More date format variations
3. Per-category forecasting in the UI

### Medium Term
1. Manual column mapping UI
2. CSV validation before upload
3. Export analytics to PDF
4. Multi-file upload (combine statements)

### Long Term
1. Budget recommendations
2. ML-assisted subscription detection
3. Fraud-focused anomaly models (IsolationForest / autoencoders)

## Testing Strategy

**88 tests, run in CI on every push** (`.github/workflows/ci.yml`); a green suite
is what gates the backend deploy.

Every fix carries a regression test that states the defect it prevents, in its
own words — the suite doubles as the record of what has actually gone wrong here.

### Unit Tests
- CSV parser: delimiters, banner preambles, split narrations, abbreviations
- Date format detection, including ISO-vs-day-first disambiguation
- Amount normalization: European decimals, currency codes, trailing signs
- Subscription detection: cadence, dispersion bounds, variable-spend rejection
- Overspending calculation
- Reconciliation: calendar-month projection, and the
  `matched + missing == expected` invariant
- Forecast: one-off detection, and that damping must win its back-test
- Anomaly: merchant-level suppression, and that it is not a blanket amnesty

### Integration Tests
- End-to-end upload flow
- API endpoint responses
- Database operations
- Session management

### Validation Tests
- Real bank CSV files
- Edge cases (empty rows, special characters)
- Performance with large files
- Error handling

## Deployment Architecture

### Production Setup

```
┌─────────────────────────────────────────────────────────┐
│                  Cloudflare Pages                       │
│                   (viewer/ → dist)                      │
│  - Static hosting on global CDN                         │
│  - Auto-scaling                                         │
│  - HTTPS enabled                                        │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     │
┌────────────────────▼────────────────────────────────────┐
│              Render Web Service                         │
│        (api/app.py — binds to $PORT)                    │
│  - smartspend-v975.onrender.com                         │
│  - ML model loaded once at startup (models/*.joblib)    │
│  - Health checks at /health                             │
│  - /tmp for ephemeral storage                           │
└─────────────────────────────────────────────────────────┘
```

### Live URLs

- **Frontend:** `https://expenseeye.pages.dev` (Cloudflare Pages)
- **Backend:** `https://smartspend-v975.onrender.com` (Render)

### Environment Variables

**Backend (Render):**
- `CORS_ORIGINS`: `https://expenseeye.pages.dev` (the Pages URL)
- `PORT`: injected by Render; the app binds to it automatically

**Frontend (Cloudflare Pages):**
- `VITE_API_URL`: `https://smartspend-v975.onrender.com`

### Monitoring

**Health Checks:**
- Endpoint: `/health`
- Interval: 60 seconds
- Timeout: 30 seconds

**Metrics to Monitor:**
- Request latency
- Error rate
- Upload success rate
- Database size
- Disk usage (/tmp)

---

**Last Updated:** 2026-09-02  
**Version:** 3.0.0  
**Author:** ExpenseEye Team
