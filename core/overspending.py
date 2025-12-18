import sqlite3
import pandas as pd


def detect_overspending(db_path="smartspend.db"):
    """
    Detects overspending months using historical baseline logic.
    Returns a list of dictionaries with overspending details.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        List of dictionaries containing overspending month details:
        - month: Month identifier (YYYY-MM)
        - spending: Total spending for the month
        - avg_spending: Historical average spending
        - std_spending: Historical standard deviation
        - pct_deviation: Percentage deviation from average
        - status: "OVERSPENDING" or "NORMAL"
        - excess: Amount overspent (only if overspending)
    """
    # Connect to database
    conn = sqlite3.connect(db_path)
    
    # Fetch all expense transactions
    query = '''
        SELECT txn_date, amount
        FROM transactions
        WHERE amount < 0
        ORDER BY txn_date
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert txn_date to datetime and extract year-month
    df['txn_date'] = pd.to_datetime(df['txn_date'])
    df['month'] = df['txn_date'].dt.to_period('M')
    
    # Aggregate spending by month
    monthly_spending = df.groupby('month')['amount'].sum().reset_index()
    monthly_spending.columns = ['month', 'total_spending']
    
    # Convert spending to positive values for easier interpretation
    monthly_spending['total_spending'] = abs(monthly_spending['total_spending'])
    
    # Sort months chronologically to enable historical baseline calculation
    monthly_spending = monthly_spending.sort_values('month').reset_index(drop=True)
    
    # Store analysis results
    results = []
    
    # Analyze each month
    for index, row in monthly_spending.iterrows():
        month = str(row['month'])
        spending = row['total_spending']
        
        # Skip first 3 months (insufficient history)
        if index < 3:
            continue
        
        # Calculate baseline using ONLY previous months (no data leakage)
        historical_data = monthly_spending.loc[:index-1, 'total_spending']
        avg_spending = historical_data.mean()
        std_spending = historical_data.std()
        
        # Handle degenerate standard deviation (zero or NaN)
        if pd.isna(std_spending) or std_spending == 0:
            std_spending = avg_spending * 0.1
        
        # Calculate overspending thresholds
        threshold_120_percent = avg_spending * 1.2
        threshold_std = avg_spending + std_spending
        
        # Calculate percentage deviation from average
        pct_deviation = ((spending - avg_spending) / avg_spending) * 100
        
        # Determine if overspending
        is_overspending = (spending > threshold_120_percent) or (spending > threshold_std)
        status = "OVERSPENDING" if is_overspending else "NORMAL"
        
        # Build result dictionary
        result = {
            'month': month,
            'spending': spending,
            'avg_spending': avg_spending,
            'std_spending': std_spending,
            'pct_deviation': pct_deviation,
            'status': status
        }
        
        if is_overspending:
            result['excess'] = spending - avg_spending
        
        results.append(result)
    
    return results
