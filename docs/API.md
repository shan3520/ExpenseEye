# API Reference

## Base URL

**Production:** `https://smartspend-v975.onrender.com`  
**Local Development:** `http://localhost:5000`

> The examples below use `https://your-app.onrender.com` as a placeholder —
> substitute the production URL above (or your own deployment).

---

## Authentication

No authentication required. Session-based access using UUID session IDs.

Pass the session id in the **`X-Session-Id` header**. A `?session_id=` query
parameter is still accepted as a fallback, but the header is preferred: a
session id in a URL ends up in browser history, proxy logs and `Referer`
headers, which is the wrong place for the key to someone's statement.

```bash
curl -H "X-Session-Id: 550e8400-e29b-41d4-a716-446655440000" \
     https://smartspend-v975.onrender.com/forecast
```

Reads return **404** once a session has been deleted or reaped, rather than an
empty result, so a client can tell "gone" from "nothing found".

---

## Endpoints

### 1. Health Check

Check if the API is running.

**Endpoint:** `GET /health`

**Request:**
```bash
curl https://your-app.onrender.com/health
```

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- `200 OK`: Service is healthy

---

### 2. Upload CSV

Upload a bank statement CSV file and create a new session.

**Endpoint:** `POST /upload`

**Request:**
```bash
curl -X POST https://your-app.onrender.com/upload \
  -F "file=@statement.csv"
```

**Request Headers:**
- `Content-Type: multipart/form-data`

**Request Body:**
- `file`: CSV file (max 10MB)

**Success Response:**
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
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

**Error Response:**
```json
{
  "success": false,
  "error": "Could not identify date column. Your CSV has: [Post Date, Value Date, Cheque Number, Debit, Credit, Balance]. Expected one of: date, transaction_date, txn_date, posting_date, value_date"
}
```

**Status Codes:**
- `200 OK`: File processed successfully
- `400 Bad Request`: Invalid file or parsing error
- `413 Payload Too Large`: File exceeds 10MB

**Notes:**
- Session ID is valid for the duration of the server session
- Database is created in `/tmp/ExpenseEye_{session_id}.db`
- Automatically detects CSV format

---

### 3. Get Subscriptions

Retrieve detected subscriptions for a session.

**Endpoint:** `GET /subscriptions`

**Query Parameters:**
- `session_id` (required): UUID from upload response

**Request:**
```bash
curl "https://your-app.onrender.com/subscriptions?session_id=550e8400-e29b-41d4-a716-446655440000"
```

**Success Response:**
```json
{
  "success": true,
  "subscriptions": [
    {
      "description": "Netflix",
      "amount": -15.99,
      "frequency": "MONTHLY",
      "avg_gap": 30.2,
      "occurrences": 12
    },
    {
      "description": "Spotify",
      "amount": -9.99,
      "frequency": "MONTHLY",
      "avg_gap": 29.8,
      "occurrences": 8
    }
  ]
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Session not found or expired"
}
```

**Status Codes:**
- `200 OK`: Subscriptions retrieved successfully
- `400 Bad Request`: Missing or invalid session_id
- `404 Not Found`: Session database not found

**Notes:**
- Requires minimum 3 occurrences to detect subscription
- Only detects debit transactions (amount < 0)
- Frequency is either "MONTHLY" or "WEEKLY"

---

### 4. Get Overspending Analysis

Retrieve overspending analysis for a session.

**Endpoint:** `GET /overspending`

**Query Parameters:**
- `session_id` (required): UUID from upload response

**Request:**
```bash
curl "https://your-app.onrender.com/overspending?session_id=550e8400-e29b-41d4-a716-446655440000"
```

**Success Response:**
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
    },
    {
      "month": "2024-07",
      "total_spending": 4200.0,
      "avg_spending": 3500.0,
      "pct_deviation": 20.0,
      "status": "OVERSPENDING"
    }
  ]
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Session not found or expired"
}
```

**Status Codes:**
- `200 OK`: Analysis retrieved successfully
- `400 Bad Request`: Missing or invalid session_id
- `404 Not Found`: Session database not found

**Notes:**
- Requires minimum 4 months of data (3-month baseline + 1 to analyze)
- Only returns months flagged as "OVERSPENDING"
- Uses statistical thresholds (120% of average OR avg + std_dev)

---

### 5. Cash-Flow Forecast (ML)

Forecast upcoming spending for a session.

**Endpoint:** `GET /forecast`

**Query Parameters:**
- `session_id` (required): UUID from upload response

**Request:**
```bash
curl "https://your-app.onrender.com/forecast?session_id=550e8400-e29b-41d4-a716-446655440000"
```

**Success Response (abridged):**
```json
{
  "success": true,
  "method": "Holt-Winters (ExponentialSmoothing)",
  "history_days": 547,
  "history_months": 18,
  "next_30_day_total": 64080.40,
  "next_month_total": 66216.41,
  "totals_basis": "both from the monthly model; 30-day figure is the month forecast scaled by 30/31",
  "one_offs": {
    "count": 1,
    "total": 84999.0,
    "charges": [{ "date": "2025-06-18", "description": "UPI-CROMA ELECTRONICS", "amount": 84999.0 }]
  },
  "one_offs_excluded_from_training": true,
  "accuracy": {
    "mae": 8010.41, "rmse": 9120.3, "mape": 12.74,
    "holdout_months": 4,
    "basis": "monthly totals, rolling one-step-ahead holdout (1 one-off charge excluded from training)"
  },
  "accuracy_alternative": { "mae": 60803.63, "rmse": 68015.14, "mape": 102.33 },
  "daily_accuracy": { "mae": 2269.64, "rmse": 5202.48, "mape": 145.69, "holdout_days": 30 },
  "monthly": {
    "history": [{ "month": "2023-01", "spend": 47000.0 }],
    "forecast": [{ "month": "2024-07", "spend": 66216.41 }]
  },
  "daily": { "history": [{ "date": "2023-01-02", "spend": 1800.0 }], "forecast": [{ "date": "2024-07-01", "spend": 1842.3 }] }
}
```

**Notes:**
- Uses `statsmodels` Holt-Winters; falls back to a moving-average/linear-trend
  baseline when history is sparse (< ~60 daily points or < 6 months).
- Never raises on sparse data — `accuracy` may be `null` if there's too little
  history to back-test.
- **Both headline totals come from the same model.** `next_30_day_total` is
  `next_month_total` scaled by `30 / days-in-month`, described in
  `totals_basis`. They previously came from two independent models and could
  disagree by ~47% on screen.
- **One-off charges are excluded from what the model learns**, never hidden. A
  charge qualifies only if it is not part of a recurring series, is large on a
  robust z-score, *and* is ≥20% of its own month. The exclusion must then win a
  back-test against the raw totals actually spent, so a misfire is caught rather
  than shipped: `one_offs_excluded_from_training` reports whether it was
  applied, `one_offs` names the charges, `accuracy_alternative` gives the
  rejected candidate's score, and `monthly.history` still contains the spike.

---

### 6. Transaction Categorization (ML)

Categorize every transaction in a session.

**Endpoint:** `GET /categorize`

**Query Parameters:**
- `session_id` (required): UUID from upload response

**Success Response (abridged):**
```json
{
  "success": true,
  "model_available": true,
  "confidence_threshold": 0.45,
  "counts": { "total": 613, "model": 580, "rule_fallback": 33 },
  "breakdown": [{ "category": "rent", "total_spend": 396000.0 }],
  "transactions": [
    { "description": "NETFLIX", "amount": -499.0, "category": "subscriptions", "confidence": 0.94, "source": "model" }
  ]
}
```

**Notes:**
- TF-IDF (word + char n-grams) → LogisticRegression, loaded once at startup.
- Predictions below `confidence_threshold` use a keyword rule fallback
  (`source: "rule_fallback"`).

---

### 7. Model Card (ML)

Return the categorizer's held-out evaluation metrics. No session required.

**Endpoint:** `GET /model-card`

**Success Response (abridged):**
```json
{
  "success": true,
  "model": "TF-IDF (word 1-2gram + char 3-5gram) + LogisticRegression",
  "n_samples": 405,
  "n_classes": 9,
  "metrics": { "accuracy": 0.9314, "macro_precision": 0.9379, "macro_recall": 0.9301, "macro_f1": 0.9306 },
  "per_class": { "groceries": { "precision": 0.91, "recall": 0.91, "f1": 0.91, "support": 11 } },
  "confusion_matrix": { "labels": ["dining", "groceries", "..."], "matrix": [[10, 1, 0]] }
}
```

---

### 8. Anomaly Detection (ML)

Flag unusual transactions for a session.

**Endpoint:** `GET /anomalies`

**Query Parameters:**
- `session_id` (required): UUID from upload response

**Success Response (abridged):**
```json
{
  "success": true,
  "method": "Robust per-category z-score (median + MAD)",
  "z_threshold": 3.5,
  "total_transactions": 525,
  "subscription_transactions_excluded": 39,
  "routine_for_merchant_suppressed": 27,
  "anomaly_count": 1,
  "anomalies": [
    {
      "txn_date": "2025-05-14", "description": "UPI-CROMA ELECTRONICS",
      "category": "shopping", "amount": -78999.0, "spend": 78999.0,
      "z_score": 83.1, "category_median": 1646.0,
      "explanation": "78999 is 48.0x the typical shopping spend (~1646); robust z-score 83.1 exceeds 3.5. It is also 48.0x this merchant's usual ~1646."
    }
  ]
}
```

**Notes — two things are deliberately NOT flagged:**

- **Detected subscriptions.** A predictable monthly charge is a subscription,
  not an unexplained outlier. They stay in the population (removing them would
  gut the statistics on subscription-heavy statements) but are excluded from
  candidacy. Count in `subscription_transactions_excluded`.
- **Charges that are ordinary for their own merchant.** A category is a coarse
  bucket — petrol (₹900–2,600) shares `transport` with bike taxis (₹45–190), so
  every fill scores a huge category z-score. On one statement that produced 28
  flags of which **27 were the same petrol station**, and something that happens
  27 times is a pattern, not an anomaly. A charge must now be unusual for its
  category **and** for its merchant. Count in
  `routine_for_merchant_suppressed`, so "found nothing" stays distinguishable
  from "ruled these out".

  This is not an amnesty: it applies only to merchants seen ≥4 times, so a
  one-off from a first-time merchant is still flagged, and a familiar merchant
  can still make a charge that does not belong — the explanation then states the
  merchant comparison alongside the category one.

---

### 9. Recurring Reconciliation

Reconcile the **expected** recurring ledger against what the statement actually
contains. This is the finance-ops loop: throughput, a measured match rate, and a
two-sided exception list.

**Endpoint:** `GET /reconcile`

**Headers:** `X-Session-Id: <uuid>`

**Success Response (abridged):**
```json
{
  "success": true,
  "method": "Expected recurring ledger vs actual charges (cadence + amount-band matching)",
  "summary": {
    "series_reconciled": 5,
    "expected_occurrences": 40,
    "matched": 39,
    "matched_clean": 39,
    "matched_with_variance": 0,
    "missing": 1,
    "unscheduled": 0,
    "match_rate": 97.5
  },
  "series": [
    {
      "merchant": "POS 4218XXXX9031 PULSE FITNESS", "frequency": "MONTHLY",
      "cadence_days": 30.0, "expected": 8, "matched": 7, "missing": 1,
      "with_variance": 0, "lapsed": false, "last_seen": "2025-08-17"
    }
  ],
  "exceptions": {
    "missing": [
      {
        "merchant": "POS 4218XXXX9031 PULSE FITNESS",
        "expected_date": "2025-06-17", "expected_amount": -1499.0,
        "frequency": "MONTHLY",
        "reason": "No charge found within 10 days of the expected date"
      }
    ],
    "unscheduled": []
  }
}
```

**Notes:**
- `matched + missing == expected_occurrences` is an invariant, enforced by a
  test. Every expected occurrence is accounted for; nothing is quietly dropped.
- The exception list is **two-sided**: `missing` (an expected charge that never
  landed) and `unscheduled` (a charge from a recurring merchant that no expected
  occurrence explains — a duplicate or an off-cycle bill).
- A series that simply stopped is reported as `lapsed` rather than generating
  phantom `missing` rows for every month since.
- Monthly and quarterly schedules are projected by **calendar month** (same day
  of month, clamped for short months), not a fixed day count. A fixed count
  accumulates ~half a day of error per cycle, so on a multi-year statement the
  projection drifts outside tolerance and every later charge is reported *both*
  as missing and as unscheduled. On a 75-month series that produced a fake 71.2%
  with 21 missing and 23 unscheduled; the correct answer is 100% with an empty
  exception list.

---

### 10. Delete Session

Delete a session's server-side data immediately, backing the "deleted on exit"
promise in the UI. Called by the frontend on **End session**.

**Endpoint:** `DELETE /session/<session_id>`

**Response:** `204 No Content`. Idempotent — deleting an already-gone session
also returns 204, so a client never has to handle a race.

```bash
curl -X DELETE https://smartspend-v975.onrender.com/session/550e8400-e29b-41d4-a716-446655440000
```

---

### 11. Preview CSV

Inspect a CSV's detected structure **without** creating a session or storing
anything — used to show the user what the auto-mapper found before they commit.

**Endpoint:** `POST /preview-csv`

**Request:** `multipart/form-data` with a `file` field, same as `/upload`.

---

## Data Models

### Subscription Object

```typescript
{
  description: string,      // Representative raw description
  amount: number,           // Median charge, negative (debit)
  amount_min: number,       // Observed range, so a price change is visible
  amount_max: number,
  frequency: string,        // "WEEKLY" | "FORTNIGHTLY" | "MONTHLY" | "QUARTERLY"
  avg_gap: number,          // MEDIAN days between charges, not the mean
  occurrences: number       // Charges in the series
}
```

### Overspending Object

```typescript
{
  month: string,            // "YYYY-MM"
  spending: number,         // Total spent that month
  avg_spending: number,     // Mean of EVERY prior month
  std_spending: number,     // Std dev of prior months (10% floor if degenerate)
  pct_deviation: number,    // Percentage above/below the baseline
  z_score: number,          // Deviation in sigma
  excess: number,
  status: string            // "OVERSPENDING" | "NORMAL"
}
```

A month is flagged when spending exceeds **120% of the baseline OR baseline +
2σ**. The two arms catch different failures: the percentage arm catches a steady
drift upward that never breaks 2σ on noisy data, and the sigma arm catches a
genuine spike in a month whose baseline is unusually low. Requiring both
conditions together missed each of those cases. No data leakage — only months
strictly before the one being judged are used, and the first 3 are skipped.
```

### Mapping Info Object

```typescript
{
  date_column: string,           // Detected date column name
  date_format: string,           // "YYYY-MM-DD (ISO-8601)" | "DD/MM/YYYY" | "MM/DD/YYYY"
  description_column: string,    // Detected column, "colA + colB" when the
                                 // narration is split, or a placeholder message
  amount_pattern: string,        // "DrCr (...)" | "Debit/Credit (...)" | "Signed Amount (...)"
  rows_skipped: number,          // Rows that could not be loaded
  skipped_rows: [                // ...and WHY, capped at 100
    { row: number | null, reason: string, values: string[] }
  ]
}
```

`skipped_rows` is the loader's own exception list. A row is never dropped
silently: an unparseable date, a malformed amount or a ragged line comes back
with its index, a stated reason and the offending values, so 500 good rows are
not lost to one bad line and the user can see exactly what was left out.

`description_column` may name **two columns joined with `+`**. Some exports split
the narration across a rail column (`UPI`/`NEFT`/`ATM`, always present) and a
counterparty column that is blank for ATM withdrawals, interest and cheques.
Taking only one stored 27% of a real statement as `UNKNOWN` and discarded the
rail. They are recombined only when the chosen column has gaps, and a
`category`/`label`/`tag` column is never folded in — appending a label would hand
the classifier the answer.

---

## Error Handling

### Error Response Format

All errors return JSON with this structure:

```json
{
  "success": false,
  "error": "Human-readable error message"
}
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "No file provided" | Missing file in request | Include file in multipart form data |
| "No file selected" | Empty filename | Select a valid file |
| "CSV file exceeds maximum size limit of 10MB" | File too large | Reduce file size or split into multiple files |
| "Could not identify date column" | No recognized date column | Check CSV has a date column with supported name |
| "Could not identify amount pattern" | No amount columns found | Verify CSV has Debit/Credit or Amount columns |
| "No valid transactions found in CSV file" | All rows failed parsing | Check CSV format and data validity |
| "Session not found or expired" | Invalid session_id | Re-upload CSV to create new session |

---

## Rate Limiting

**Current:** No rate limiting implemented

**Recommended for Production:**
- 10 uploads per minute per IP
- 100 analytics requests per minute per session

---

## File Size Limits

- **Maximum file size:** 10MB
- **Recommended:** < 5MB for best performance
- **Typical bank statement:** 1-2MB

---

## Session Management

### Session Lifecycle

1. **Creation:** Upload CSV → Generate UUID → Create database
2. **Active:** Session ID valid while server running
3. **Expiration:** Server restart or manual cleanup

### Session Storage

- **Location:** `/tmp/ExpenseEye_{session_id}.db`
- **Format:** SQLite database
- **Cleanup:** Automatic on server restart (ephemeral storage)

### Best Practices

- Store session_id on client side
- Re-upload if session expires
- Don't share session_ids (no authentication)

---

## CSV Format Requirements

### Minimum Requirements

1. **Date Column:** One of the supported date column names
2. **Amount Column(s):** One of the supported amount patterns
3. **Valid Data:** At least one parseable transaction row

### Supported Column Names

**Date:**
- `Date`, `Transaction Date`, `Txn Date`, `Posting Date`, `Value Date`

**Description (optional):**
- `Description`, `Name`, `Narration`, `Merchant`, `Details`, `Particulars`, `Remarks`

**Amount Patterns:**

**Pattern 1:** DrCr + Amount
- Columns: `DrCr` (or `Type`), `Amount`
- Values: `DR`/`CR` or `Debit`/`Credit`

**Pattern 2:** Debit + Credit
- Columns: `Debit`, `Credit`
- Values: Numeric (one column empty per row)

**Pattern 3:** Signed Amount
- Column: `Amount`
- Values: Negative for debits, positive for credits

A running **`Balance` is deliberately NOT accepted as a transaction amount** — a
balance is a stock, not a flow, and loading it as spend produces confident
nonsense. A file whose only money column is a balance is rejected with a message
that says exactly that, rather than parsing "successfully" and being wrong.

**Header matching also handles:**
- **Metadata rows above the header.** Bank exports open with a banner
  ("Statement of Account", account number, period). The real header is located
  even when those lines carry fewer fields than it does.
- **Abbreviations with periods** — `Withdrawal Amt.`, `Chq./Ref.No.`. All
  non-alphanumerics are stripped before matching.
- **Currency qualifiers** — `Amount (INR)`, `Amount in USD`. Via an explicit
  allow-list, so `Amount Outstanding` and `Amount Due` are still rejected.
- **Non-comma delimiters** — `;`, tab and `|` are sniffed, since European
  exports commonly use semicolons.
- **A missing/blank header** for the narration, via a content heuristic that
  picks the column whose values are mostly free text.

### Date Format Support

- **YYYY-MM-DD** (ISO-8601, detected first and parsed as ISO)
- **DD/MM/YYYY** (auto-detected)
- **MM/DD/YYYY** (auto-detected)
- Dash, slash and dot separators; 2-digit years

Order is detected for the column as a whole, not per row. ISO is checked first
and parsed explicitly: letting a day-first parser near `2024-03-01` silently
stored it as 3 January, reporting `rows_skipped: 0` while every date was wrong.
Dates outside a plausible range (before 1990 or more than 2 years ahead) are
skipped with a reason rather than being trusted.

---

## Examples

### Complete Upload Flow

```python
import requests

# 1. Upload CSV
with open('statement.csv', 'rb') as f:
    response = requests.post(
        'https://your-app.onrender.com/upload',
        files={'file': f}
    )

data = response.json()
if data['success']:
    session_id = data['session_id']
    print(f"Loaded {data['transactions_loaded']} transactions")
    
    # 2. Get subscriptions
    subs_response = requests.get(
        f'https://your-app.onrender.com/subscriptions',
        params={'session_id': session_id}
    )
    subscriptions = subs_response.json()['subscriptions']
    
    # 3. Get overspending
    over_response = requests.get(
        f'https://your-app.onrender.com/overspending',
        params={'session_id': session_id}
    )
    overspending = over_response.json()['overspending']
    
    print(f"Found {len(subscriptions)} subscriptions")
    print(f"Found {len(overspending)} overspending months")
else:
    print(f"Error: {data['error']}")
```

### JavaScript Example

```javascript
// Upload CSV
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('https://your-app.onrender.com/upload', {
  method: 'POST',
  body: formData
})
.then(res => res.json())
.then(data => {
  if (data.success) {
    const sessionId = data.session_id;
    
    // Get subscriptions
    return fetch(`https://your-app.onrender.com/subscriptions?session_id=${sessionId}`);
  }
})
.then(res => res.json())
.then(data => {
  console.log('Subscriptions:', data.subscriptions);
});
```

---

## Changelog

### v3.0.0 (2026-09-02)
- **`/reconcile`** — the finance-ops loop: expected recurring ledger vs actual
  charges, reporting a match rate and a two-sided exception list
- **`DELETE /session/<id>`** and **`POST /preview-csv`** documented
- Session id moved to the **`X-Session-Id` header** (query param still accepted);
  reads return 404 once a session is gone
- `/forecast`: both headline totals now come from one model (`totals_basis`);
  one-off charges excluded from training only when the exclusion wins a
  back-test (`one_offs`, `one_offs_excluded_from_training`,
  `accuracy_alternative`)
- `/anomalies`: a charge that is routine for its own merchant is no longer
  flagged (`routine_for_merchant_suppressed`) — one statement produced 28 flags
  of which 27 were the same petrol station
- `mapping_info.skipped_rows` — every skipped row with a stated reason;
  `description_column` may name two columns joined with `+` for split narrations
- Loader: ISO-8601 dates parsed explicitly, banner preambles, abbreviations with
  periods, currency-qualified headers, `;`/tab/`|` delimiters; a running
  `Balance` is no longer accepted as a transaction amount
- Reconciliation projects monthly schedules by calendar month, not a fixed day
  count, which had faked the match rate on long statements
- Categorizer: `cash` and `fees` categories; prefix-anchored rule matching
- Served by **gunicorn** rather than the Werkzeug development server

### v2.0.0 (2026-06-02)
- **ML features:** `/forecast` (Holt-Winters cash-flow forecast), `/categorize`
  (TF-IDF + LogisticRegression categorizer), `/model-card`, `/anomalies`
  (robust z-score anomaly detection)
- CSV loader hardened: thousands separators, currency symbols, CR/DR markers,
  parentheses negatives; content-based description-column fallback
- App binds to `$PORT`; `render.yaml` Blueprint added

### v1.0.0 (2024-12-19)
- Initial API release
- CSV upload with auto-detection
- Subscription detection
- Overspending analysis
- Session-based architecture

---

**Last Updated:** 2026-09-02  
**API Version:** 2.0.0  
**Base URL:** https://smartspend-v975.onrender.com
