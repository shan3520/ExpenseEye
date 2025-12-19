import sqlite3
import pandas as pd
import re


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


def detect_description_column(columns):
    """Detect description column from CSV headers. Returns None if not found."""
    aliases = ['description', 'name', 'narration', 'merchant', 'details', 'particulars', 'remarks']
    normalized = {normalize_column_name(col): col for col in columns}
    
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    
    # Description is optional - return None if not found
    return None


def detect_amount_pattern(columns):
    """Detect amount representation pattern in CSV."""
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
    
    if drcr_col and amount_col:
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
    
    # Pattern C: Signed Amount
    signed_aliases = amount_aliases + ['balance']
    for alias in signed_aliases:
        if alias in normalized:
            return ('signed', normalized[alias])
    
    # Show what columns were actually found
    available_cols = ', '.join(columns[:10])
    raise ValueError(f"Could not identify amount columns. Your CSV has: [{available_cols}]. Expected one of: (1) DrCr + Amount, (2) Debit + Credit columns, or (3) signed Amount column.")


def normalize_amount(row, pattern, col1, col2=None):
    """Normalize amount based on detected pattern."""
    try:
        if pattern == 'drcr':
            drcr_value = str(row[col1]).strip() if not pd.isna(row[col1]) else ''
            # Normalize: uppercase and remove non-alphabet characters
            drcr_value = re.sub(r'[^A-Z]', '', drcr_value.upper())
            amount_value = row[col2]
            
            if pd.isna(amount_value):
                return None
            
            amount_value = float(amount_value)
            
            if drcr_value in ['DB', 'DR', 'D', 'DEBIT', 'WITHDRAWAL', 'W']:
                return -abs(amount_value)
            elif drcr_value in ['CR', 'C', 'CREDIT', 'DEPOSIT', 'DEP']:
                return abs(amount_value)
            else:
                return None
        
        elif pattern == 'debit_credit':
            debit_val = row[col1] if not pd.isna(row[col1]) else 0
            credit_val = row[col2] if not pd.isna(row[col2]) else 0
            
            try:
                debit_val = float(debit_val) if debit_val else 0
                credit_val = float(credit_val) if credit_val else 0
            except (ValueError, TypeError):
                return None
            
            return credit_val - debit_val
        
        elif pattern == 'signed':
            amount_value = row[col1]
            
            if pd.isna(amount_value):
                return None
            
            return float(amount_value)
        
    except (ValueError, TypeError, KeyError):
        return None
    
    return None


def find_header_row(csv_path):
    """
    Find the actual header row in a CSV that may have metadata rows at the top.
    Returns the row number where the actual headers are.
    """
    # Try reading first 20 rows to find headers
    try:
        # Read without assuming headers
        df_preview = pd.read_csv(csv_path, nrows=20, header=None)
        
        # Look for rows that contain common column keywords
        date_keywords = ['date', 'transaction', 'txn', 'posting', 'value']
        desc_keywords = ['description', 'name', 'narration', 'merchant', 'details', 'particulars']
        amount_keywords = ['amount', 'debit', 'credit', 'balance', 'value', 'withdrawal', 'deposit']
        
        for idx, row in df_preview.iterrows():
            # Convert row to lowercase strings
            row_str = [str(val).lower().strip() for val in row if pd.notna(val)]
            
            # Check if this row contains typical column headers
            has_date = any(keyword in ' '.join(row_str) for keyword in date_keywords)
            has_desc = any(keyword in ' '.join(row_str) for keyword in desc_keywords)
            has_amount = any(keyword in ' '.join(row_str) for keyword in amount_keywords)
            
            # If we found at least 2 of the 3 required column types, this is likely the header
            if sum([has_date, has_desc, has_amount]) >= 2:
                return idx
        
        # If no header found, assume first row
        return 0
    except:
        return 0


def detect_date_format(df, date_col):
    """
    Auto-detect if dates are in DD/MM/YYYY or MM/DD/YYYY format.
    Returns True if dayfirst (DD/MM/YYYY), False if monthfirst (MM/DD/YYYY).
    """
    # Sample first 10 non-null dates
    sample_dates = df[date_col].dropna().head(10)
    
    if len(sample_dates) == 0:
        return True  # Default to DD/MM/YYYY (international standard)
    
    # Try parsing with dayfirst=True and dayfirst=False
    # Count how many parse successfully with each method
    dayfirst_success = 0
    monthfirst_success = 0
    
    for date_str in sample_dates:
        # Try dayfirst (DD/MM/YYYY)
        try:
            parsed = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
            if not pd.isna(parsed):
                dayfirst_success += 1
        except:
            pass
        
        # Try monthfirst (MM/DD/YYYY)
        try:
            parsed = pd.to_datetime(date_str, dayfirst=False, errors='coerce')
            if not pd.isna(parsed):
                monthfirst_success += 1
        except:
            pass
    
    # If both work equally, check for ambiguous dates
    # Look for dates where day > 12 (can't be month)
    for date_str in sample_dates:
        date_str = str(date_str).strip()
        parts = date_str.replace('-', '/').split('/')
        
        if len(parts) >= 3:
            try:
                first_part = int(parts[0])
                second_part = int(parts[1])
                
                # If first part > 12, it must be day (DD/MM/YYYY)
                if first_part > 12:
                    return True
                
                # If second part > 12, it must be day (MM/DD/YYYY)
                if second_part > 12:
                    return False
            except:
                continue
    
    # Default to DD/MM/YYYY (international standard used by most countries)
    return True


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
    
    # Read CSV file with detected header row
    try:
        df = pd.read_csv(csv_path, header=header_row)
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e:
        raise ValueError(f"Failed to parse CSV file: {str(e)}")
    
    if df.empty:
        raise ValueError("CSV file is empty or contains no data rows.")
    
    # Detect columns
    date_col = detect_date_column(df.columns)
    desc_col = detect_description_column(df.columns)
    amount_pattern_info = detect_amount_pattern(df.columns)
    
    # Auto-detect date format
    dayfirst = detect_date_format(df, date_col)
    date_format_type = "DD/MM/YYYY" if dayfirst else "MM/DD/YYYY"
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
        
        # Insert data row by row
        rows_inserted = 0
        rows_skipped = 0
        
        for index, row in df.iterrows():
            try:
                # Parse transaction date with auto-detected format
                txn_date = pd.to_datetime(row[date_col], errors='coerce', dayfirst=dayfirst)
                if pd.isna(txn_date):
                    rows_skipped += 1
                    continue
                txn_date = txn_date.date()
                
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
                    print(f"[CSV Loader] Skipping row {index}: Invalid amount")
                    rows_skipped += 1
                    continue
                
                # Insert into database
                cursor.execute(
                    'INSERT INTO transactions (txn_date, description, amount) VALUES (?, ?, ?)',
                    (txn_date, description, amount)
                )
                rows_inserted += 1
                
            except Exception as e:
                print(f"[CSV Loader] Skipping row {index}: {str(e)}")
                rows_skipped += 1
                continue
        
        # Commit the transaction
        conn.commit()
        
        if rows_inserted == 0:
            raise ValueError("No valid transactions found in CSV file.")
        
        mapping_info = {
            'date_column': date_col,
            'description_column': desc_col if desc_col else 'None (using TRANSACTION placeholder)',
            'amount_pattern': pattern_desc,
            'rows_skipped': rows_skipped
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
