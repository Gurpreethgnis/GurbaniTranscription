"""Test database search functionality."""
from scripture.sggs_db import SGGSDatabase

db = SGGSDatabase()

# Test search with Gurmukhi text
print("Testing search with Gurmukhi text...")
results = db.search_by_text("ਵਾਹਿਗੁਰੂ", top_k=3)
print(f"Found {len(results)} results")

if results:
    print("\nFirst result:")
    r = results[0]
    print(f"  Line ID: {r.line_id}")
    print(f"  Gurmukhi: {r.gurmukhi[:100]}")
    print(f"  Ang: {r.ang}")
    print(f"  Raag: {r.raag}")
    print(f"  Author: {r.author}")

# Test search with English/Roman text (might not work, but let's try)
print("\nTesting search with English text...")
results2 = db.search_by_text("wahiguru", top_k=3)
print(f"Found {len(results2)} results")

# Test getting a specific line
print("\nTesting get_line_by_id...")
if results:
    line = db.get_line_by_id(results[0].line_id)
    if line:
        print(f"Retrieved line: {line.gurmukhi[:100]}")
        print(f"Ang: {line.ang}, Raag: {line.raag}")

db.close()
print("\nDatabase search test complete!")
