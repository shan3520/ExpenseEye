# API Reference

## Base URL

**Production:** `https://your-app.onrender.com`  
**Local Development:** `http://localhost:5000`

---

## Authentication

No authentication required. Session-based access using UUID session IDs.

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
- Database is created in `/tmp/smartspend_{session_id}.db`
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

## Data Models

### Subscription Object

```typescript
{
  description: string,      // Transaction description
  amount: number,           // Negative amount (debit)
  frequency: string,        // "MONTHLY" or "WEEKLY"
  avg_gap: number,          // Average days between payments
  occurrences: number       // Number of times detected
}
```

### Overspending Object

```typescript
{
  month: string,            // "YYYY-MM" format
  total_spending: number,   // Total spent in month (negative)
  avg_spending: number,     // Historical average
  pct_deviation: number,    // Percentage above average
  status: string            // "OVERSPENDING" or "NORMAL"
}
```

### Mapping Info Object

```typescript
{
  date_column: string,           // Detected date column name
  description_column: string,    // Detected description column (or placeholder message)
  amount_pattern: string,        // "DrCr (...)" | "Debit/Credit (...)" | "Signed Amount (...)"
  rows_skipped: number           // Number of invalid rows skipped
}
```

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

- **Location:** `/tmp/smartspend_{session_id}.db`
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
- Column: `Amount` (or `Balance`)
- Values: Negative for debits, positive for credits

### Date Format Support

- **DD/MM/YYYY** (auto-detected)
- **MM/DD/YYYY** (auto-detected)
- **YYYY-MM-DD** (ISO format)
- **DD-MM-YYYY** (dash separator)
- **MM-DD-YYYY** (dash separator)

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

### v1.0.0 (2024-12-19)
- Initial API release
- CSV upload with auto-detection
- Subscription detection
- Overspending analysis
- Session-based architecture

---

**Last Updated:** 2024-12-19  
**API Version:** 1.0.0  
**Base URL:** https://your-app.onrender.com
