"""Check database encoding and test searches."""
from scripture.sggs_db import SGGSDatabase
import sqlite3

db = SGGSDatabase()

# Get a sample line and check its encoding
cursor = db._connection.execute("SELECT id, gurmukhi, source_page FROM lines LIMIT 1")
sample = cursor.fetchone()

if sample:
    gurmukhi = sample['gurmukhi']
    print(f"Sample line ID: {sample['id']}")
    print(f"Source page: {sample['source_page']}")
    print(f"Gurmukhi text (first 100 chars): {gurmukhi[:100]}")
    print(f"Text type: {type(gurmukhi)}")
    print(f"Text encoding check:")
    
    # Check if it's Unicode Gurmukhi
    gurmukhi_unicode_range = any('\u0A00' <= char <= '\u0A7F' for char in gurmukhi[:50])
    print(f"  Contains Unicode Gurmukhi (0A00-0A7F): {gurmukhi_unicode_range}")
    
    # Check for ASCII transliteration patterns
    ascii_pattern = any(c.isascii() and c.isalpha() for c in gurmukhi[:50])
    print(f"  Contains ASCII characters: {ascii_pattern}")
    
    # Try searching with the actual format from sample
    print(f"\nTrying search with sample text pattern...")
    if 'siq' in gurmukhi.lower() or 'nwmu' in gurmukhi.lower():
        # Try searching for ASCII transliteration
        test_search = "siq"
        cursor2 = db._connection.execute("SELECT COUNT(*) FROM lines WHERE gurmukhi LIKE ?", (f"%{test_search}%",))
        count = cursor2.fetchone()[0]
        print(f"  Lines containing 'siq': {count}")
        
        if count > 0:
            cursor3 = db._connection.execute("SELECT id, gurmukhi, source_page FROM lines WHERE gurmukhi LIKE ? LIMIT 3", (f"%{test_search}%",))
            results = cursor3.fetchall()
            print(f"  Found {len(results)} results")
            for r in results:
                print(f"    ID: {r['id']}, Page: {r['source_page']}, Text: {r['gurmukhi'][:50]}")

db.close()
