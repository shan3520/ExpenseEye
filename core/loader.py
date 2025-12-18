import sqlite3
import pandas as pd


def load_csv_to_db(csv_path, db_path):
    """
    Load bank statement CSV into a session-specific SQLite database.
    
    Supports various CSV formats from different banks and open banking providers.
    Handles case-insensitive column names and multiple amount representations.
    
    Args:
        csv_path: Path to the CSV file to load
        db_path: Path where the SQLite database should be created
        
    Returns:
        int: Number of transactions loaded
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format cannot be parsed
        sqlite3.Error: If database operations fail
    """
    # Read CSV file
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)}")
    
    if df.empty:
        raise ValueError("CSV file is empty")
    
    # Normalize column names to lowercase for case-insensitive matching
    df.columns = df.columns.str.strip().str.lower()
    
    # Detect date column
    date_col = None
    for col_name in ['date', 'transaction_date', 'txn_date', 'transaction date', 'txndate']:
        if col_name in df.columns:
            date_col = col_name
            break
    
    if not date_col:
        raise ValueError("Unsupported CSV format. Expected date, description, and amount fields.")
    
    # Detect description column
    desc_col = None
    for col_name in ['name', 'description', 'narration', 'merchant', 'details', 'particulars']:
        if col_name in df.columns:
            desc_col = col_name
            break
    
    if not desc_col:
        raise ValueError("Unsupported CSV format. Expected date, description, and amount fields.")
    
    # Detect amount representation
    # Option 1: DrCr column with amount
    # Option 2: Separate debit and credit columns
    # Option 3: Single signed amount column
    
    amount_mode = None
    drcr_col = None
    amount_col = None
    debit_col = None
    credit_col = None
    
    # Check for DrCr column
    for col_name in ['drcr', 'dr/cr', 'type', 'transaction_type', 'txn_type']:
        if col_name in df.columns:
            drcr_col = col_name
            # Find corresponding amount column
            for amt_name in ['amount', 'amt', 'value', 'transaction_amount']:
                if amt_name in df.columns:
                    amount_col = amt_name
                    amount_mode = 'drcr'
                    break
            if amount_mode:
                break
    
    # Check for separate debit/credit columns
    if not amount_mode:
        for debit_name in ['debit', 'debit_amount', 'withdrawal', 'dr']:
            if debit_name in df.columns:
                debit_col = debit_name
                break
        
        for credit_name in ['credit', 'credit_amount', 'deposit', 'cr']:
            if credit_name in df.columns:
                credit_col = credit_name
                break
        
        if debit_col and credit_col:
            amount_mode = 'debit_credit'
    
    # Check for single signed amount column
    if not amount_mode:
        for amt_name in ['amount', 'amt', 'value', 'transaction_amount', 'balance']:
            if amt_name in df.columns:
                amount_col = amt_name
                amount_mode = 'signed'
                break
    
    if not amount_mode:
        raise ValueError("Unsupported CSV format. Expected date, description, and amount fields.")
    
    print(f"[CSV Loader] Detected columns - Date: {date_col}, Description: {desc_col}, Amount mode: {amount_mode}")
    
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
                # Parse transaction date
                txn_date = pd.to_datetime(row[date_col], errors='coerce')
                if pd.isna(txn_date):
                    rows_skipped += 1
                    continue
                txn_date = txn_date.date()
                
                # Get description
                description = row[desc_col]
                if pd.isna(description):
                    description = 'UNKNOWN'
                else:
                    description = str(description).strip()
                
                # Calculate amount based on detected mode
                amount = None
                
                if amount_mode == 'drcr':
                    # DrCr column with amount
                    drcr_value = str(row[drcr_col]).strip().upper() if not pd.isna(row[drcr_col]) else ''
                    amt_value = row[amount_col]
                    
                    if pd.isna(amt_value):
                        rows_skipped += 1
                        continue
                    
                    amt_value = float(amt_value)
                    
                    # Check for debit indicators
                    if drcr_value in ['DB', 'D', 'DR', 'DEBIT', 'WITHDRAWAL']:
                        amount = -abs(amt_value)
                    # Check for credit indicators
                    elif drcr_value in ['CR', 'C', 'CREDIT', 'DEPOSIT']:
                        amount = abs(amt_value)
                    else:
                        # If unclear, skip row
                        rows_skipped += 1
                        continue
                
                elif amount_mode == 'debit_credit':
                    # Separate debit and credit columns
                    debit_val = row[debit_col] if not pd.isna(row[debit_col]) else 0
                    credit_val = row[credit_col] if not pd.isna(row[credit_col]) else 0
                    
                    try:
                        debit_val = float(debit_val) if debit_val else 0
                        credit_val = float(credit_val) if credit_val else 0
                    except (ValueError, TypeError):
                        rows_skipped += 1
                        continue
                    
                    # Debit is negative, credit is positive
                    amount = credit_val - debit_val
                
                elif amount_mode == 'signed':
                    # Single signed amount column
                    amt_value = row[amount_col]
                    
                    if pd.isna(amt_value):
                        rows_skipped += 1
                        continue
                    
                    try:
                        amount = float(amt_value)
                    except (ValueError, TypeError):
                        rows_skipped += 1
                        continue
                
                if amount is None:
                    rows_skipped += 1
                    continue
                
                # Insert into database
                cursor.execute(
                    'INSERT INTO transactions (txn_date, description, amount) VALUES (?, ?, ?)',
                    (txn_date, description, amount)
                )
                rows_inserted += 1
                
            except Exception as e:
                # Skip problematic rows instead of crashing
                rows_skipped += 1
                continue
        
        # Commit the transaction
        conn.commit()
        
        if rows_skipped > 0:
            print(f"[CSV Loader] Skipped {rows_skipped} rows due to parsing errors")
        
        if rows_inserted == 0:
            raise ValueError("No valid transactions found in CSV file")
        
        return rows_inserted
        
    except Exception as e:
        # Rollback on error
        conn.rollback()
        raise
        
    finally:
        # Always close the connection
        conn.close()
