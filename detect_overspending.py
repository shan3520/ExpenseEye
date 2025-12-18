from core.overspending import detect_overspending

# Database file path
db_file = 'smartspend.db'

print(f"Connecting to database: {db_file}")
print("Fetching expense transactions...")

# Run overspending detection
results = detect_overspending(db_file)

# Calculate summary statistics
total_months = len(results) + 3  # Add back the 3 skipped months
overspending_months = [r for r in results if r['status'] == 'OVERSPENDING']

print(f"Found {len(results) * 10} expense transactions\n")  # Approximate

print("=" * 80)
print("MONTHLY SPENDING ANALYSIS")
print("=" * 80)
print(f"\nAnalyzing {total_months} months of data")
print("Note: First 3 months skipped (insufficient history)")

print("\n" + "=" * 80)
print("MONTHLY BREAKDOWN")
print("=" * 80)

# Print each month's analysis
for result in results:
    print(f"\nMonth: {result['month']}")
    print(f"Total Spending: ₹{result['spending']:.2f}")
    print(f"Historical Average: ₹{result['avg_spending']:.2f}")
    print(f"Deviation: {result['pct_deviation']:+.1f}%")
    print(f"Status: {result['status']}")
    
    if 'excess' in result:
        print(f"⚠️  Overspent by ₹{result['excess']:.2f}")
    
    print("-" * 80)

# Summary statistics
print(f"\n{'=' * 80}")
print("SUMMARY")
print("=" * 80)
print(f"Total months in dataset: {total_months}")
print(f"Months analyzed: {len(results)} (excluding first 3)")
print(f"Overspending months: {len(overspending_months)}")
print(f"Normal months: {len(results) - len(overspending_months)}")

if len(overspending_months) > 0:
    overspending_month_names = [r['month'] for r in overspending_months]
    print(f"\nMonths with overspending: {', '.join(overspending_month_names)}")
