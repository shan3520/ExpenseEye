import sqlite3
import pandas as pd


def load_csv_to_db(csv_path, db_path):
    """
    Load bank statement CSV into a session-specific SQLite database.
    
    This function creates a new transactions table and populates it with
    data from the CSV file. It normalizes debit/credit transactions into
    a single amount field (negative for debits, positive for credits).
    
    Args:
        csv_path: Path to the CSV file to load
        db_path: Path where the SQLite database should be created
        
    Returns:
        int: Number of transactions loaded
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV is malformed or missing required columns
        sqlite3.Error: If database operations fail
    """
    # Read CSV file
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e:
        raise ValueError(f"Failed to read CSV file: {str(e)}")
    
    # Validate required columns
    required_columns = ['date', 'name', 'DrCr', 'amount']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV missing required columns: {missing_columns}")
    
    # Connect to SQLite database (creates file if it doesn't exist)
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
        
        # Clear existing data (in case DB already exists)
        cursor.execute('DELETE FROM transactions')
        
        # Insert data row by row
        rows_inserted = 0
        
        for index, row in df.iterrows():
            # Parse transaction date
            txn_date = pd.to_datetime(row['date']).date()
            
            # Handle missing description
            description = row['name']
            if pd.isna(description):
                description = 'UNKNOWN'
            
            # Normalize amount: negative for debit, positive for credit
            if row['DrCr'] == 'Db':
                amount = -float(row['amount'])
            elif row['DrCr'] == 'Cr':
                amount = float(row['amount'])
            else:
                # Skip rows with invalid DrCr values
                continue
            
            # Insert into database
            cursor.execute(
                'INSERT INTO transactions (txn_date, description, amount) VALUES (?, ?, ?)',
                (txn_date, description, amount)
            )
            rows_inserted += 1
        
        # Commit the transaction
        conn.commit()
        
        return rows_inserted
        
    except Exception as e:
        # Rollback on error
        conn.rollback()
        raise sqlite3.Error(f"Database operation failed: {str(e)}")
        
    finally:
        # Always close the connection
        conn.close()
