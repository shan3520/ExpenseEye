"""
ExpenseEye CSV Auto-Mapper - Intelligent CSV parser for bank statements

Copyright (c) 2024 Shantanu (shan3520)
Original Repository: https://github.com/shan3520/expenseeye
License: MIT
"""

import sqlite3
from datetime import date

import pandas as pd
import re

# Unique implementation identifier - DO NOT REMOVE
# This code is part of ExpenseEye by Shantanu (shan3520)
# Original: https://github.com/shan3520/expenseeye
# If you find this elsewhere, it's a derivative work
_EXPENSEEYE_IMPLEMENTATION = "shan3520-expenseeye-csv-automapper-v1.0-20241219"
_ORIGINAL_AUTHOR = "Shantanu (shan3520)"
_ORIGINAL_REPO = "https://github.com/shan3520/expenseeye"

# Plausible transaction-date window. Anything outside is a typo or a corrupt
# row, not real history: a mistyped year (1900 / 2099 / 9999) would otherwise
# stretch every downstream time series across centuries.
_MIN_PLAUSIBLE_YEAR = 1990
_MAX_YEARS_AHEAD = 2

# Recognized debit/credit indicator tokens (uppercased, non-alpha stripped).
# Shared by the DrCr column content-validator and normalize_amount so they
# always agree on what counts as a sign indicator.
_DEBIT_TOKENS = {"DB", "DR", "D", "DEBIT", "WITHDRAWAL", "W", "PURCHASE"}
_CREDIT_TOKENS = {"CR", "C", "CREDIT", "DEPOSIT", "DEP", "REFUND", "REVERSAL"}


def normalize_column_name(col):
    """Normalize column name for matching."""
    col = str(col).lower().strip()
    col = re.sub(r'[_\s\-/]+', '', col)
    return col


def detect_date_column(columns):
    """Detect date column from CSV headers."""
    aliases = ['date', 'transactiondate', 'txndate', 'postingdate', 'valuedate']
    normalized = {normalize_column_name(col): col for col in columns}
    
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    
    # Show what columns were actually found
    available_cols = ', '.join(columns[:10])  # Show first 10 columns
    raise ValueError(f"Could not identify date column. Your CSV has: [{available_cols}]. Expected one of: date, transaction_date, txn_date, posting_date, value_date.")


def detect_description_column(columns, df=None, exclude=None):
    """
    Detect the description column.

    First tries known header aliases. If none match and the DataFrame is
    provided, falls back to a content heuristic: pick the non-excluded column
    whose values are mostly free text (not numeric, not dates). This rescues
    statements whose narration sits under a blank / "Unnamed" header. Columns
    that are entirely empty are ignored, so exports with no narration at all
    correctly yield None.

    Returns the column name, or None if no description could be identified.
    """
    aliases = ['description', 'name', 'narration', 'merchant', 'details', 'particulars', 'remarks']
    normalized = {normalize_column_name(col): col for col in columns}

    for alias in aliases:
        if alias in normalized:
            return normalized[alias]

    # Content-based fallback.
    if df is not None:
        exclude = set(exclude or [])
        best_col, best_score = None, 0.0
        for col in columns:
            if col in exclude:
                continue
            series = df[col].dropna()
            if len(series) == 0:
                continue  # all-empty column (e.g. blank "Unnamed") -> skip
            text_hits = 0
            for val in series:
                s = str(val).strip()
                if s == '':
                    continue
                # "Text" = not parseable as a number and contains a letter.
                if coerce_amount(s) is None and re.search(r'[A-Za-z]{2,}', s):
                    text_hits += 1
            score = text_hits / len(series)
            # Require a clear majority of text values, and prefer the richest.
            if score >= 0.6 and score > best_score:
                best_col, best_score = col, score
        if best_col is not None:
            return best_col

    # Description is optional - return None if not found
    return None


def _looks_like_drcr(series):
    """
    True if a majority of a column's non-null values are recognizable
    debit/credit indicator tokens (DR/CR/DEBIT/CREDIT/PURCHASE/REFUND/...).

    Guards against an unrelated column literally named "Type" (holding values
    like Purchase/Refund/Online/POS) hijacking the DrCr pattern.
    """
    try:
        sample = list(series.dropna()[:30])
    except AttributeError:
        return False
    if not sample:
        return False
    hits = 0
    for v in sample:
        tok = re.sub(r'[^A-Z]', '', str(v).upper())
        if tok in _DEBIT_TOKENS or tok in _CREDIT_TOKENS:
            hits += 1
    return hits >= 0.6 * len(sample)


def detect_amount_pattern(columns, df=None):
    """
    Detect amount representation pattern in CSV.

    When a DataFrame is provided, a candidate DrCr column is accepted only if
    its VALUES actually look like debit/credit indicators, so a column merely
    named "Type" cannot hijack the DrCr pattern and reject every row.
    """
    normalized = {normalize_column_name(col): col for col in columns}

    # Pattern A: DrCr + Amount
    drcr_aliases = ['drcr', 'type', 'transactiontype', 'txntype']
    amount_aliases = ['amount', 'amt', 'value', 'transactionamount']

    drcr_col = None
    amount_col = None

    for alias in drcr_aliases:
        if alias in normalized:
            drcr_col = normalized[alias]
            break

    for alias in amount_aliases:
        if alias in normalized:
            amount_col = normalized[alias]
            break

    if drcr_col and amount_col and (df is None or _looks_like_drcr(df[drcr_col])):
        return ('drcr', drcr_col, amount_col)

    # Pattern B: Debit + Credit
    debit_aliases = ['debit', 'withdrawal', 'debitamount', 'dr', 'withdrawalamount', 'withdrawalamt']
    credit_aliases = ['credit', 'deposit', 'creditamount', 'cr', 'depositamount', 'depositamt']
    
    debit_col = None
    credit_col = None
    
    for alias in debit_aliases:
        if alias in normalized:
            debit_col = normalized[alias]
            break
    
    for alias in credit_aliases:
        if alias in normalized:
            credit_col = normalized[alias]
            break
    
    if debit_col and credit_col:
        return ('debit_credit', debit_col, credit_col)
    
    # Pattern C: Signed Amount. A running Balance is a stock, not a flow, so it
    # is deliberately NOT treated as a transaction amount (see P1-9 below).
    signed_aliases = amount_aliases
    for alias in signed_aliases:
        if alias in normalized:
            return ('signed', normalized[alias])

    # Nothing matched. If the only money-like column is a running balance, say
    # so explicitly rather than silently loading the balance as the amount.
    if 'balance' in normalized:
        raise ValueError(
            "Found a 'Balance' column but no transaction amount column. A running "
            "balance is not a transaction amount — provide a Debit/Credit, "
            "DrCr + Amount, or signed Amount column."
        )

    # Show what columns were actually found
    available_cols = ', '.join(columns[:10])
    raise ValueError(f"Could not identify amount columns. Your CSV has: [{available_cols}]. Expected one of: (1) DrCr + Amount, (2) Debit + Credit columns, or (3) signed Amount column.")


def _normalize_decimal(s):
    """
    Normalize a numeric string's thousands / decimal separators to a plain
    float literal, or return None if the separator pattern is malformed.

    Handles US ("1,250.50"), European ("1.234,56" / "1 234,56") and plain
    forms, and rejects nonsense like "1,2,3" instead of concatenating it.
    """
    s = re.sub(r'[\s ]', '', s)   # spaces (incl. NBSP) act as thousands sep
    neg = s.startswith('-')
    s = s.lstrip('+-')
    if not s or not re.fullmatch(r'[0-9.,]+', s):
        return None

    has_comma = ',' in s
    has_dot = '.' in s

    if has_comma and has_dot:
        # Whichever separator appears LAST is the decimal point.
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')   # European: '.' thousands, ',' decimal
        else:
            s = s.replace(',', '')                      # US/Indian: ',' thousands, '.' decimal
    elif has_comma:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) == 2:
            s = parts[0] + '.' + parts[1]               # decimal comma (1234,56)
        elif 1 <= len(parts[0]) <= 3 and all(len(p) == 3 for p in parts[1:]):
            s = ''.join(parts)                          # thousands grouping (1,234,567)
        else:
            return None                                  # malformed (1,2,3)
    elif has_dot:
        parts = s.split('.')
        if len(parts) == 2:
            pass                                         # single dot = decimal point
        elif 1 <= len(parts[0]) <= 3 and all(len(p) == 3 for p in parts[1:]):
            s = ''.join(parts)                          # dot thousands (1.234.567)
        else:
            return None

    return ('-' + s) if neg else s


def coerce_amount(value):
    """
    Parse a possibly messy numeric cell into a float, or None if not numeric.

    Handles thousands separators ("28,840.00"), currency symbols and codes
    ("₹1,200", "INR 500"), trailing CR/DR markers ("49,429.72 CR"), parentheses
    negatives ("(150.00)"), trailing-minus negatives ("500-") and the European
    decimal-comma convention ("1.234,56"). Malformed separator patterns
    ("1,2,3") are rejected rather than silently concatenated. Callers that
    already know the sign (Debit/Credit or DrCr columns) operate on the magnitude.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)

    s = str(value).strip()
    if s == '' or s.lower() in ('nan', 'none', 'na'):
        return None

    sign = 1.0
    # Parentheses denote a negative amount in many statement formats.
    if s.startswith('(') and s.endswith(')'):
        sign = -1.0
        s = s[1:-1].strip()
    # Trailing CR / DR marker (e.g. "1,234.50 DR").
    marker = re.search(r'([CD]R)\s*$', s, re.IGNORECASE)
    if marker:
        if marker.group(1).upper() == 'DR':
            sign = -1.0
        s = s[:marker.start()].strip()
    # Pull a leading sign off BEFORE stripping currency codes: the code regex is
    # anchored, so "-Rs.500" would otherwise keep its "Rs." and fail to parse.
    lead = re.match(r'^([+-])\s*', s)
    if lead:
        if lead.group(1) == '-':
            sign = -sign
        s = s[lead.end():].strip()
    # Currency codes appear on either side in real exports ("INR 500", "500 INR").
    _CODE = r'(?:INR|USD|EUR|GBP|RS\.?)'
    s = re.sub(rf'^{_CODE}\s*', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(rf'\s*{_CODE}$', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'[₹$€£]', '', s).strip()
    # Trailing '-' as a negative sign (common in SAP / legacy exports).
    if s.endswith('-'):
        sign = -sign
        s = s[:-1].strip()

    s = _normalize_decimal(s)
    if s is None or s in ('', '-', '+', '.'):
        return None
    try:
        return sign * float(s)
    except ValueError:
        return None


def normalize_amount(row, pattern, col1, col2=None):
    """Normalize amount based on detected pattern."""
    try:
        if pattern == 'drcr':
            drcr_value = str(row[col1]).strip() if not pd.isna(row[col1]) else ''
            # Normalize: uppercase and remove non-alphabet characters
            drcr_value = re.sub(r'[^A-Z]', '', drcr_value.upper())

            amount_value = coerce_amount(row[col2])
            if amount_value is None:
                return None

            if drcr_value in _DEBIT_TOKENS:
                return -abs(amount_value)
            elif drcr_value in _CREDIT_TOKENS:
                return abs(amount_value)
            else:
                return None

        elif pattern == 'debit_credit':
            # Coerce both columns; treat blank / non-numeric cells as 0 so that
            # a row with only a debit (or only a credit) still parses.
            debit_val = coerce_amount(row[col1]) or 0.0
            credit_val = coerce_amount(row[col2]) or 0.0

            # If both are 0, skip this row
            if debit_val == 0 and credit_val == 0:
                return None

            return credit_val - debit_val

        elif pattern == 'signed':
            return coerce_amount(row[col1])

    except (ValueError, TypeError, KeyError):
        return None

    return None


def sniff_delimiter(csv_path, default=','):
    """
    Detect the column delimiter from the first non-empty lines.

    Indian/US exports use commas, but European bank exports commonly use
    semicolons (and some use tabs or pipes). Guessing wrong makes the whole file
    look like one column, which then fails column detection entirely.
    """
    candidates = [',', ';', '	', '|']
    try:
        with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
            lines = [ln for ln in (f.readline() for _ in range(10)) if ln and ln.strip()]
    except OSError:
        return default
    if not lines:
        return default
    best, best_score = default, 0
    for cand in candidates:
        counts = [ln.count(cand) for ln in lines]
        if not counts or max(counts) == 0:
            continue
        consistent = sum(1 for c in counts if c == counts[0] and c > 0)
        score = counts[0] * consistent
        if score > best_score:
            best, best_score = cand, score
    return best


def find_header_row(csv_path):
    """
    Find the actual header row in a CSV that may have metadata rows at the top.
    Returns the row number where the actual headers are.
    """
    # Try reading first 20 rows to find headers
    try:
        # Read without assuming headers
        df_preview = pd.read_csv(csv_path, nrows=20, header=None,
                                 sep=sniff_delimiter(csv_path), engine='python')
        
        # Look for rows that contain common column keywords
        date_keywords = ['date', 'transaction', 'txn', 'posting', 'value']
        desc_keywords = ['description', 'name', 'narration', 'merchant', 'details', 'particulars']
        amount_keywords = ['amount', 'debit', 'credit', 'balance', 'value', 'withdrawal', 'deposit']
        
        def _cell_matches(cells, keywords):
            """Match a keyword against a whole cell token, not any substring of
            the joined row. Substring matching let the generic keyword "value"
            match a DATA cell like "value1", so a data row was picked as the
            header and the error then quoted a value as a column name."""
            for cell in cells:
                tokens = re.split(r'[^a-z0-9]+', cell)
                for kw in keywords:
                    if ' ' in kw:
                        if kw in cell:
                            return True
                    elif kw in tokens:
                        return True
            return False

        for idx, row in df_preview.iterrows():
            # Convert row to lowercase strings
            row_str = [str(val).lower().strip() for val in row if pd.notna(val)]
            
            # Check if this row contains typical column headers
            has_date = _cell_matches(row_str, date_keywords)
            has_desc = _cell_matches(row_str, desc_keywords)
            has_amount = _cell_matches(row_str, amount_keywords)
            
            # If we found at least 2 of the 3 required column types, this is likely the header
            if sum([has_date, has_desc, has_amount]) >= 2:
                return idx
        
        # If no header found, assume first row
        return 0
    except Exception:
        return 0


def detect_date_format(df, date_col):
    """
    Detect the date component order used by a column.

    Returns one of:
      'ISO'        - YYYY-MM-DD (ISO-8601); parsed year-first so day and month
                     are never transposed
      'DAYFIRST'   - DD/MM/YYYY
      'MONTHFIRST' - MM/DD/YYYY
    """
    # Sample first 10 non-null dates
    sample_dates = df[date_col].dropna().head(10)

    if len(sample_dates) == 0:
        return 'DAYFIRST'  # international default

    # ISO-8601 (year-first) is unambiguous and MUST be detected before the
    # day/month heuristic below: an ISO date starts with a 4-digit year, so the
    # "component > 12" test never fires and pandas(dayfirst=True) would silently
    # transpose day and month (2024-03-01 read as 3 Jan instead of 1 Mar).
    iso_re = re.compile(r'^\s*\d{4}-\d{1,2}-\d{1,2}')
    iso_hits = sum(1 for d in sample_dates if iso_re.match(str(d)))
    if iso_hits >= max(1, int(0.6 * len(sample_dates))):
        return 'ISO'

    # Ambiguous slash / dash / dot formats: a component > 12 disambiguates.
    for date_str in sample_dates:
        parts = re.split(r'[/\-.]', str(date_str).strip())
        if len(parts) >= 3:
            try:
                first_part = int(parts[0])
                second_part = int(parts[1])
            except (ValueError, TypeError):
                continue
            # If the first component > 12 it must be the day (DD/MM/YYYY).
            if first_part > 12:
                return 'DAYFIRST'
            # If the second component > 12 it must be the day (MM/DD/YYYY).
            if second_part > 12:
                return 'MONTHFIRST'

    # Default to day-first (international standard used by most countries).
    return 'DAYFIRST'


def load_csv_to_db(csv_path, db_path):
    """
    Load bank statement CSV into a session-specific SQLite database.
    Auto-detects column mappings and normalizes data.
    
    Args:
        csv_path: Path to the CSV file to load
        db_path: Path where the SQLite database should be created
        
    Returns:
        tuple: (transactions_loaded, mapping_info)
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format cannot be parsed
        sqlite3.Error: If database operations fail
    """
    # Find the actual header row
    header_row = find_header_row(csv_path)
    
    # Read CSV file with detected header row. Ragged rows (a wrong column
    # count) are captured and skipped instead of aborting the whole upload
    # (P1-7): 500 good rows should not be lost because of one bad line.
    malformed_lines = []

    def _collect_bad_line(bad_line):
        if len(malformed_lines) < 100:
            malformed_lines.append([str(c) for c in bad_line])
        return None  # drop this row and keep going

    try:
        df = pd.read_csv(
            csv_path, header=header_row, sep=sniff_delimiter(csv_path),
            engine='python', on_bad_lines=_collect_bad_line,
        )
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {str(e)}")
    
    if df.empty:
        raise ValueError("CSV file is empty or contains no data rows.")
    
    # Detect columns. Amount/date columns are detected first so they can be
    # excluded from the content-based description fallback.
    date_col = detect_date_column(df.columns)
    amount_pattern_info = detect_amount_pattern(df.columns, df=df)
    _amount_cols = [c for c in amount_pattern_info[1:] if c]
    desc_col = detect_description_column(
        df.columns, df=df, exclude=[date_col, *_amount_cols]
    )
    
    # Auto-detect date format (ISO-8601 year-first, day-first, or month-first).
    date_order = detect_date_format(df, date_col)
    date_format_type = {
        'ISO': 'YYYY-MM-DD (ISO-8601)',
        'MONTHFIRST': 'MM/DD/YYYY',
        'DAYFIRST': 'DD/MM/YYYY',
    }[date_order]
    print(f"[CSV Auto-Mapper] Detected date format: {date_format_type}")
    
    pattern = amount_pattern_info[0]
    
    if pattern == 'drcr':
        drcr_col = amount_pattern_info[1]
        amount_col = amount_pattern_info[2]
        pattern_desc = f"DrCr ({drcr_col} + {amount_col})"
    elif pattern == 'debit_credit':
        debit_col = amount_pattern_info[1]
        credit_col = amount_pattern_info[2]
        pattern_desc = f"Debit/Credit ({debit_col} + {credit_col})"
    else:
        amount_col = amount_pattern_info[1]
        pattern_desc = f"Signed Amount ({amount_col})"
    
    
    
    # Parse all transaction dates in one vectorized pass instead of calling
    # pd.to_datetime per row (far cheaper on large statements). ISO-8601 is
    # parsed year-first (format='ISO8601') so day and month are never swapped.
    if date_order == 'ISO':
        parsed_dates = pd.to_datetime(df[date_col], errors='coerce', format='ISO8601')
    else:
        parsed_dates = pd.to_datetime(
            df[date_col], errors='coerce', dayfirst=(date_order == 'DAYFIRST')
        )

    # Connect to SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                txn_date DATE,
                description TEXT,
                amount REAL
            )
        ''')
        
        # Clear existing data
        cursor.execute('DELETE FROM transactions')
        
        # Build the rows first, then insert them all in one executemany call.
        _max_plausible_year = date.today().year + _MAX_YEARS_AHEAD
        rows_inserted = 0
        to_insert = []
        # Structured exception list (P2-13): each skipped row records why it was
        # dropped and the raw values, so the API/UI can show an honest account
        # instead of a bare count. Capped so a pathological file can't blow up.
        skipped_details = []
        skipped_count = 0

        def _record_skip(idx, reason, values):
            nonlocal skipped_count
            skipped_count += 1
            if len(skipped_details) < 100:
                skipped_details.append({"row": idx, "reason": reason, "values": values})

        # CSV-level malformed rows never made it into the DataFrame.
        for bad in malformed_lines:
            _record_skip(None, "Malformed CSV row (wrong number of columns)", bad)

        for pos, (_, row) in enumerate(df.iterrows()):
            raw_values = [str(v) for v in row.values][:8]
            try:
                # Use the pre-parsed (vectorized) date for this row.
                txn_date = parsed_dates.iat[pos]
                if pd.isna(txn_date):
                    _record_skip(pos, f"Unparseable date: {str(row[date_col])!r}", raw_values)
                    continue
                txn_date = txn_date.date()
                if not (_MIN_PLAUSIBLE_YEAR <= txn_date.year <= _max_plausible_year):
                    _record_skip(
                        pos,
                        f"Date {txn_date} outside the plausible range "
                        f"{_MIN_PLAUSIBLE_YEAR}-{_max_plausible_year}",
                        raw_values,
                    )
                    continue

                # Get description (use placeholder if column doesn't exist)
                if desc_col:
                    description = row[desc_col]
                    if pd.isna(description):
                        description = 'UNKNOWN'
                    else:
                        description = str(description).strip()
                else:
                    description = 'TRANSACTION'

                # Calculate amount
                if pattern == 'drcr':
                    amount = normalize_amount(row, 'drcr', drcr_col, amount_col)
                elif pattern == 'debit_credit':
                    amount = normalize_amount(row, 'debit_credit', debit_col, credit_col)
                else:
                    amount = normalize_amount(row, 'signed', amount_col)

                if amount is None:
                    _record_skip(pos, "Invalid or unrecognized amount", raw_values)
                    continue

                to_insert.append((txn_date, description, amount))
                rows_inserted += 1

            except Exception as e:
                _record_skip(pos, f"{type(e).__name__}: {e}", raw_values)
                continue

        rows_skipped = skipped_count

        # Batch insert every valid row in a single round-trip.
        if to_insert:
            cursor.executemany(
                'INSERT INTO transactions (txn_date, description, amount) VALUES (?, ?, ?)',
                to_insert
            )

        # Commit the transaction
        conn.commit()
        
        if rows_inserted == 0:
            raise ValueError("No valid transactions found in CSV file.")
        
        mapping_info = {
            'date_column': date_col,
            'date_format': date_format_type,
            'description_column': desc_col if desc_col else 'None (using TRANSACTION placeholder)',
            'amount_pattern': pattern_desc,
            'rows_skipped': rows_skipped,
            # Structured exception list (capped at 100) so consumers can show
            # exactly which rows were dropped and why (P2-13).
            'skipped_rows': skipped_details,
        }
        
        return rows_inserted, mapping_info
        
    except ValueError as ve:
        # Re-raise ValueError with original message
        conn.rollback()
        raise ve
    except Exception as e:
        conn.rollback()
        # Log the actual error for debugging
        print(f"[CSV Loader Error] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise ValueError(f"Failed to process CSV file. Error: {str(e)}")
        
    finally:
        conn.close()
