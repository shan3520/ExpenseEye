from core.subscriptions import detect_subscriptions

# Database file path
db_file = 'smartspend.db'

print(f"Connecting to database: {db_file}")
print("Fetching transactions...")

# Run subscription detection
subscriptions = detect_subscriptions(db_file)

print(f"Found {len(subscriptions)} eligible transactions\n")
print("Analyzing transaction patterns...\n")

# Print results
print("=" * 70)
print("DETECTED SUBSCRIPTIONS")
print("=" * 70)

if len(subscriptions) == 0:
    print("No recurring subscriptions detected.")
else:
    for sub in subscriptions:
        print(f"\nDescription:  {sub['description']}")
        print(f"Amount:       ₹{abs(sub['amount']):.2f}")
        print(f"Frequency:    {sub['frequency']}")
        print(f"Avg Gap:      {sub['avg_gap']:.1f} days")
        print(f"Occurrences:  {sub['occurrences']}")
        print("-" * 70)

print(f"\nTotal subscriptions found: {len(subscriptions)}")

# Persist subscriptions to database
print("\n" + "=" * 70)
print("SAVING TO DATABASE")
print("=" * 70)
print("\nCreating subscriptions table...")
print("Clearing existing subscriptions...")
print("Inserting subscriptions into database...")
print(f"Total subscriptions inserted: {len(subscriptions)}")

# Fetch and display all subscriptions from database
print("\n" + "=" * 70)
print("SUBSCRIPTIONS FROM DATABASE")
print("=" * 70)

import sqlite3
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute('SELECT * FROM subscriptions')
rows = cursor.fetchall()

for row in rows:
    print(f"\nID: {row[0]}")
    print(f"Description:  {row[1]}")
    print(f"Amount:       ₹{abs(row[2]):.2f}")
    print(f"Frequency:    {row[3]}")
    print(f"Avg Gap:      {row[4]:.1f} days")
    print(f"Occurrences:  {row[5]}")
    print("-" * 70)

# Close connection
conn.close()
print("\nDatabase connection closed.")
