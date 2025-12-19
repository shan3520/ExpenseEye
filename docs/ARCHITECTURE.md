# SmartSpend Architecture

## System Overview

SmartSpend follows a **three-tier architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                      │
│                    (viewer/app.py)                          │
│  - File upload UI                                           │
│  - Analytics visualization                                  │
│  - Session management                                       │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
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
│  │              │  │     .py      │  │     .py      │     │
│  │ CSV Auto-    │  │ Subscription │  │ Overspending │     │
│  │ Mapper       │  │ Detection    │  │ Analysis     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │
┌────────────────────▼────────────────────────────────────────┐
│                 SQLite Database (Ephemeral)                 │
│                   /tmp/smartspend_{uuid}.db                 │
│  - transactions table                                       │
│  - Session-scoped                                           │
│  - Auto-cleanup                                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer (Streamlit)

**File:** `viewer/app.py`

**Responsibilities:**
- User interface for CSV upload
- Display analytics results
- Session state management
- Error handling and user feedback

**Key Features:**
- File upload with drag-and-drop
- Real-time analytics display
- CSV format preview
- Responsive design

**Technology Stack:**
- Streamlit 1.29+
- Requests (HTTP client)
- Pandas (data display)

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

detect_description_column(columns)
# Identifies description column (optional)

detect_amount_pattern(columns)
# Detects: DrCr, Debit/Credit, or Signed Amount

detect_date_format(df, date_col)
# Auto-detects DD/MM/YYYY vs MM/DD/YYYY

normalize_amount(row, pattern, *cols)
# Converts various amount formats to float

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
- Each upload creates a new database: `/tmp/smartspend_{uuid}.db`
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
Streamlit sends to /upload
    ↓
Flask validates file
    ↓
Generate session UUID
    ↓
Create temp database: /tmp/smartspend_{uuid}.db
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
Streamlit stores session_id
    ↓
Display success + format preview
```

### Analytics Flow

```
User clicks "Detect Subscriptions"
    ↓
Streamlit calls /subscriptions?session_id={uuid}
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
Streamlit displays results
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

### Short Term
1. Support for Excel files directly
2. Currency symbol handling (₹, $, €)
3. Thousand separator support (1,000.00)
4. More date format variations

### Medium Term
1. Manual column mapping UI
2. CSV validation before upload
3. Export analytics to PDF
4. Multi-file upload (combine statements)

### Long Term
1. Machine learning for better subscription detection
2. Spending category classification
3. Budget recommendations
4. Anomaly detection for fraud

## Testing Strategy

### Unit Tests
- CSV parser with various formats
- Date format detection
- Amount normalization
- Subscription detection algorithm
- Overspending calculation

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
│                   Streamlit Cloud                       │
│                  (viewer/app.py)                        │
│  - Static hosting                                       │
│  - Auto-scaling                                         │
│  - HTTPS enabled                                        │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Render Web Service                    │
│                    (api/app.py)                         │
│  - Gunicorn WSGI server                                 │
│  - Auto-scaling                                         │
│  - Health checks                                        │
│  - /tmp for ephemeral storage                           │
└─────────────────────────────────────────────────────────┘
```

### Environment Variables

**Backend (Render):**
- `FLASK_ENV`: `production`
- `MAX_CONTENT_LENGTH`: `10485760` (10MB)

**Frontend (Streamlit Cloud):**
- `API_BASE_URL`: `https://your-api.onrender.com`

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

**Last Updated:** 2024-12-19  
**Version:** 1.0.0  
**Author:** SmartSpend Team
