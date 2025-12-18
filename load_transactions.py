import sqlite3
import pandas as pd

# Database file path
db_file = 'smartspend.db'

# Read CSV file
print("Reading bankstatements.csv...")
df = pd.read_csv('bankstatements.csv')



# Connect to SQLite database (creates file if it doesn't exist)
print(f"Connecting to database: {db_file}")
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Create transactions table
print("Creating transactions table...")
cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        txn_date DATE,
        description TEXT,
        amount REAL
    )
''')

# Clear existing data (optional - remove if you want to append)
print("Clearing existing data from transactions table...")
cursor.execute('DELETE FROM transactions')

# Insert data row by row
print("Inserting transactions...")
rows_inserted = 0

for index, row in df.iterrows():
    txn_date = pd.to_datetime(row['date']).date()
    description = row['name']
    if pd.isna(description):
        description='UNKNOWN'
    # Calculate amount: negative for debit, positive for credit
    if row['DrCr']=='Db':
        amount = -float(row['amount'])
    elif row['DrCr']=='Cr':
        amount = float(row['amount'])
    else:
        continue
    
    # Insert into database
    cursor.execute(
        'INSERT INTO transactions (txn_date, description, amount) VALUES (?, ?, ?)',
        (txn_date, description, amount)
    )
    rows_inserted += 1

# Commit the transaction
conn.commit()
print(f"\nTotal rows inserted: {rows_inserted}")

# Fetch and display first 5 rows
print("\nFirst 5 rows from transactions table:")
cursor.execute('SELECT * FROM transactions LIMIT 5')
results = cursor.fetchall()

for row in results:
    print(f"ID: {row[0]}, Date: {row[1]}, Description: {row[2]}, Amount: {row[3]}")

# Close connection
conn.close()
print("\nDatabase connection closed.")
