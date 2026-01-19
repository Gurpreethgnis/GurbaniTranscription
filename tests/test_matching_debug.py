"""Debug matching process."""
from scripture.sggs_db import SGGSDatabase
from scripture.scripture_service import ScriptureService
from scripture.gurmukhi_to_ascii import try_ascii_search
from quotes.assisted_matcher import AssistedMatcher
from models import QuoteCandidate
from rapidfuzz import fuzz
import config

# Initialize
db = SGGSDatabase(db_path=config.SCRIPTURE_DB_PATH)
service = ScriptureService(sggs_db=db)
matcher = AssistedMatcher(scripture_service=service)

# Test candidate
candidate_text = "ਸਤਿ ਨਾਮੁ ਕਰਤਾ ਪੁਰਖੁ"
ascii_text = try_ascii_search(candidate_text)
print(f"Unicode: {candidate_text}")
print(f"ASCII: {ascii_text}")

# Search database
results = service.search_candidates(candidate_text, top_k=5)
print(f"\nDatabase search found: {len(results)} results")

if results:
    db_text = results[0].gurmukhi
    print(f"Database text: {db_text[:60]}")
    
    # Test fuzzy matching
    similarity = fuzz.token_sort_ratio(ascii_text, db_text, score_cutoff=50)
    print(f"\nFuzzy similarity: {similarity}%")
    
    # Test word overlap
    search_words = set(ascii_text.split())
    line_words = set(db_text.split())
    overlap = search_words.intersection(line_words)
    print(f"Search words: {search_words}")
    print(f"Line words (first 10): {list(line_words)[:10]}")
    print(f"Overlap: {overlap}")
    print(f"Overlap ratio: {len(overlap) / max(len(search_words), len(line_words)):.2f}")

# Test full matching
candidate = QuoteCandidate(start=0, end=1, text=candidate_text, confidence=0.7)
match = matcher.find_match([candidate])

if match:
    print(f"\n[SUCCESS] Match found!")
    print(f"  Line ID: {match.line_id}")
    print(f"  Confidence: {match.confidence:.2f}")
else:
    print("\n[FAILED] No match found")

matcher.close()
service.close()
