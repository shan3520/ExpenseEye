# SmartSpend - Personal Finance Analytics

> Privacy-first bank statement analyzer with intelligent subscription detection and overspending alerts

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.29+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

SmartSpend is a privacy-first financial analytics platform that helps you understand your spending patterns without sharing your data with third parties. Upload your bank statement CSV, and get instant insights into recurring subscriptions and overspending months.

**Key Features:**
- 🔒 **Privacy-First**: All processing happens on your server - no data sharing
- 📊 **Smart CSV Auto-Mapper**: Handles 20+ bank CSV formats automatically
- 💳 **Subscription Detection**: Identifies recurring payments with confidence scores
- 📈 **Overspending Analysis**: Statistical detection of unusual spending months
- 🌍 **Global Support**: Auto-detects DD/MM/YYYY and MM/DD/YYYY date formats
- ⚡ **Session-Based**: Ephemeral SQLite databases - data deleted after session

## Architecture

```
smartspend/
├── api/              # Flask REST API backend
│   └── app.py        # API endpoints
├── core/             # Business logic modules
│   ├── loader.py     # CSV auto-mapper
│   ├── subscriptions.py  # Subscription detection
│   └── overspending.py   # Overspending analysis
├── viewer/           # Streamlit frontend
│   └── app.py        # UI application
└── requirements.txt  # Python dependencies
```

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/shan3520/smartspend.git
cd smartspend
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the backend API**
```bash
python api/app.py
```

4. **Run the frontend (in a new terminal)**
```bash
streamlit run viewer/app.py
```

5. **Access the application**
- Frontend: http://localhost:8501
- API: http://localhost:5000

## Deployment

### Backend (Render)

1. **Create a new Web Service** on [Render](https://render.com)
2. **Connect your GitHub repository**
3. **Configure the service:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python api/app.py`
   - **Environment:** Python 3.11

### Frontend (Streamlit Cloud)

1. **Deploy to [Streamlit Cloud](https://streamlit.io/cloud)**
2. **Connect your GitHub repository**
3. **Set the main file:** `viewer/app.py`
4. **Add secret (if needed):**
   ```toml
   API_BASE_URL = "https://your-render-app.onrender.com"
   ```

## Supported CSV Formats

SmartSpend automatically detects and handles multiple CSV formats:

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
1. Group transactions by description and amount
2. Require minimum 3 occurrences
3. Calculate day gaps between consecutive transactions
4. Classify as MONTHLY (25-35 days) or WEEKLY (5-9 days)
5. Require consistency: std_dev < 20% of average gap

**Confidence Score:**
- Based on consistency of timing
- Higher confidence = more regular payments

### Overspending Detection

**Algorithm:**
1. Calculate monthly spending totals
2. For each month (after 3-month baseline):
   - Calculate average of previous months
   - Calculate standard deviation
   - Flag if spending > 120% of average OR > avg + std_dev
3. Report percentage deviation from baseline

**Statistical Approach:**
- No data leakage: Only uses historical data
- Handles low variance with 10% minimum std_dev
- Skips first 3 months (insufficient history)

## Development

### Project Structure

```
smartspend/
├── api/
│   └── app.py                 # Flask API with session management
├── core/
│   ├── loader.py              # CSV auto-mapper with smart detection
│   ├── subscriptions.py       # Subscription detection algorithm
│   └── overspending.py        # Overspending analysis algorithm
├── viewer/
│   ├── app.py                 # Streamlit UI
│   └── requirements.txt       # Frontend dependencies
├── requirements.txt           # Backend dependencies
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

- **No external API calls**: All processing happens locally
- **Session-based storage**: SQLite databases in temp directory
- **Automatic cleanup**: Databases deleted after session expires
- **No persistent storage**: No data retention
- **File size limits**: 10MB maximum upload size
- **Input validation**: Strict CSV parsing with error handling

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

- Built with [Flask](https://flask.palletsprojects.com/) and [Streamlit](https://streamlit.io/)
- CSV parsing powered by [pandas](https://pandas.pydata.org/)
- Deployed on [Render](https://render.com) and [Streamlit Cloud](https://streamlit.io/cloud)

## Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/shan3520/smartspend/issues)
- Check existing documentation in `/docs`

---

**Made with ❤️ for privacy-conscious individuals who want to understand their spending without compromising their data.**
