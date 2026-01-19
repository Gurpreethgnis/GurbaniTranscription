"""Debug database search."""
from scripture.sggs_db import SGGSDatabase
import sqlite3

db = SGGSDatabase()

# Check what table and column are being used
tables = db._get_table_names()
print(f"Tables: {tables}")

# Check lines table structure
cursor = db._connection.execute("PRAGMA table_info(lines)")
columns = [row[1] for row in cursor.fetchall()]
print(f"\nLines table columns: {columns}")

# Check if gurmukhi column exists
if 'gurmukhi' in columns:
    print("\n[OK] gurmukhi column found!")
    
    # Try a direct query
    test_query = "SELECT id, gurmukhi, source_page FROM lines WHERE gurmukhi LIKE ? LIMIT 3"
    cursor2 = db._connection.execute(test_query, ("%ਵਾਹਿਗੁਰੂ%",))
    rows = cursor2.fetchall()
    print(f"\nDirect query results: {len(rows)} rows")
    
    if rows:
        print("\nFirst result:")
        row = rows[0]
        print(f"  ID: {row['id']}")
        print(f"  Gurmukhi: {row['gurmukhi'][:50]}")
        print(f"  Source page: {row['source_page']}")
    else:
        # Get a sample line to see the data format
        cursor4 = db._connection.execute("SELECT id, gurmukhi, source_page FROM lines LIMIT 5")
        samples = cursor4.fetchall()
        if samples:
            print(f"\nSample lines ({len(samples)}):")
            for i, sample in enumerate(samples[:3], 1):
                gurmukhi_text = sample['gurmukhi']
                print(f"\n  Sample {i}:")
                print(f"    ID: {sample['id']}")
                print(f"    Gurmukhi length: {len(gurmukhi_text)} chars")
                print(f"    First 50 chars (repr): {repr(gurmukhi_text[:50])}")
                print(f"    Source page: {sample['source_page']}")
        
        # Try searching for a common word that should exist
        print("\nTrying to find common Gurbani words...")
        test_words = ['ਵਾਹਿਗੁਰੂ', 'ਸਤਿਗੁਰੂ', 'ਗੁਰੂ']
        for word in test_words:
            cursor5 = db._connection.execute("SELECT COUNT(*) FROM lines WHERE gurmukhi LIKE ?", (f"%{word}%",))
            count = cursor5.fetchone()[0]
            print(f"  Lines containing '{word}': {count}")

db.close()
