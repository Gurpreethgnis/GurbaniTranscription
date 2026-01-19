"""Quick script to explore the ShabadOS database schema."""
from scripture.sggs_db import SGGSDatabase

db = SGGSDatabase()
tables = db._get_table_names()

print("=" * 60)
print("ShabadOS Database Schema Exploration")
print("=" * 60)
print(f"\nTotal tables: {len(tables)}")
print(f"Tables: {', '.join(tables)}")

print("\n" + "=" * 60)
print("Checking for text-containing tables...")
print("=" * 60)

for table in tables:
    cursor = db._connection.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    cols_lower = [c.lower() for c in columns]
    
    # Check if this table might contain Gurmukhi text
    has_text = any(keyword in ' '.join(cols_lower) for keyword in ['gurmukhi', 'text', 'line', 'shabad', 'gurbani'])
    
    if has_text:
        print(f"\nTable: {table}")
        print(f"  Columns: {columns}")
        
        # Get row count
        count_cursor = db._connection.execute(f"SELECT COUNT(*) FROM {table}")
        count = count_cursor.fetchone()[0]
        print(f"  Row count: {count:,}")
        
        # Get sample row if not too large
        if count > 0 and count < 100000:
            sample_cursor = db._connection.execute(f"SELECT * FROM {table} LIMIT 1")
            sample = sample_cursor.fetchone()
            if sample:
                print(f"  Sample row (first 3 columns):")
                for i, col in enumerate(columns[:3]):
                    val = str(sample[i])[:50] if sample[i] else None
                    print(f"    {col}: {val}")

print("\n" + "=" * 60)
print("Testing search functionality...")
print("=" * 60)

# Test search
results = db.search_by_text("ਵਾਹਿਗੁਰੂ", top_k=3)
print(f"\nSearch for 'ਵਾਹਿਗੁਰੂ': Found {len(results)} results")
if results:
    for i, line in enumerate(results[:3], 1):
        print(f"\n  Result {i}:")
        print(f"    Line ID: {line.line_id}")
        print(f"    Gurmukhi: {line.gurmukhi[:100]}")
        if line.ang:
            print(f"    Ang: {line.ang}")
        if line.raag:
            print(f"    Raag: {line.raag}")

db.close()
print("\n" + "=" * 60)
print("Database exploration complete!")
print("=" * 60)
