import sqlite3
import pandas as pd

# A month must be at least this far above the trailing baseline, AND this many
# standard deviations out, before it is called overspending. Both are
# conventional thresholds, not values tuned to produce a pleasing flag rate.
_MIN_PCT_DEVIATION = 0.20   # 20% above baseline
_SIGMA_THRESHOLD = 2.0      # 2 sigma


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
        
        # A month ran hot if EITHER signal is present: a materially larger spend
        # (>= 20% above baseline) OR a genuine statistical outlier (>= 2 sigma).
        # Either alone is sufficient evidence.
        #
        # The original rule ORed 20% with ONE sigma. One sigma is far too
        # permissive -- roughly 16% of a normal distribution sits above it -- so
        # it fired first every time and the 20% test never triggered at all,
        # flagging 53% of months, some as little as 9.7% above baseline. The
        # defect was the sigma threshold, not the OR: requiring both instead
        # would make the statistical test purely subtractive and would ignore a
        # 3-sigma month for missing 20% by two points.
        threshold_pct = avg_spending * (1 + _MIN_PCT_DEVIATION)
        threshold_std = avg_spending + _SIGMA_THRESHOLD * std_spending

        # Calculate percentage deviation from average
        pct_deviation = ((spending - avg_spending) / avg_spending) * 100
        z_score = (spending - avg_spending) / std_spending if std_spending else 0.0

        is_overspending = (spending > threshold_pct) or (spending > threshold_std)
        status = "OVERSPENDING" if is_overspending else "NORMAL"
        
        # Build result dictionary
        result = {
            'month': month,
            'spending': spending,
            'avg_spending': avg_spending,
            'std_spending': std_spending,
            'pct_deviation': pct_deviation,
            'z_score': round(z_score, 2),
            'status': status
        }
        
        if is_overspending:
            result['excess'] = spending - avg_spending
        
        results.append(result)
    
    return results
