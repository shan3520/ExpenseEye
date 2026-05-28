import sqlite3
import pandas as pd


def detect_subscriptions(db_path="smartspend.db"):
    """
    Runs subscription detection and persists results into DB.
    Returns a list of detected subscriptions.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        List of dictionaries containing subscription details:
        - description: Transaction description
        - amount: Transaction amount (negative)
        - frequency: "MONTHLY" or "WEEKLY"
        - avg_gap: Average days between transactions
        - occurrences: Number of times the subscription occurred
    """
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    # Fetch all transactions excluding UNKNOWN and credits
    query = '''
        SELECT txn_date, description, amount
        FROM transactions
        WHERE description != 'UNKNOWN'
        AND amount < 0
        ORDER BY description, amount, txn_date
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Vectorize datetime conversion instead of doing it per-group
    # This prevents redundant parsing overhead inside the loop
    df['txn_date'] = pd.to_datetime(df['txn_date'])

    # Group by description and amount
    grouped = df.groupby(['description', 'amount'])
    
    # Store detected subscriptions
    subscriptions = []
    
    for (description, amount), group in grouped:
        # Need at least 3 occurrences
        if len(group) < 3:
            continue
        
        # Sort dates chronologically
        dates = group['txn_date'].sort_values()
        
        # Vectorize gap calculation using pandas .diff()
        # This replaces an O(n) Python loop with a highly optimized C implementation
        gaps = dates.diff().dt.days.dropna().tolist()
        
        # Ignore highly irregular patterns
        if max(gaps) - min(gaps) > 5:
            continue
        
        # Calculate average gap
        avg_gap = round(sum(gaps) / len(gaps), 1)
        
        # Classify frequency
        frequency = None
        if 25 <= avg_gap <= 35:
            frequency = "MONTHLY"
        elif 6 <= avg_gap <= 8:
            frequency = "WEEKLY"
        
        # Only keep if we detected a frequency
        if frequency:
            subscriptions.append({
                'description': description,
                'amount': amount,
                'frequency': frequency,
                'avg_gap': avg_gap,
                'occurrences': len(group)
            })
    
    # Persist subscriptions to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create subscriptions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            amount REAL,
            frequency TEXT,
            avg_gap REAL,
            occurrences INTEGER
        )
    ''')
    
    # Clear existing data
    cursor.execute('DELETE FROM subscriptions')
    
    # Insert detected subscriptions
    for sub in subscriptions:
        cursor.execute('''
            INSERT INTO subscriptions (description, amount, frequency, avg_gap, occurrences)
            VALUES (?, ?, ?, ?, ?)
        ''', (sub['description'], sub['amount'], sub['frequency'], sub['avg_gap'], sub['occurrences']))
    
    # Commit transaction
    conn.commit()
    conn.close()
    
    return subscriptions
