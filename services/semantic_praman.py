"""
Semantic Praman Service for Shabad Mode.

Provides semantic similarity search for finding related pramans (scripture references)
based on thematic meaning and vocabulary overlap.
"""
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Set
import pickle

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("numpy not available for semantic praman service")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("faiss not available")


@dataclass
class PramanResult:
    """Result from praman similarity search."""
    line_id: str
    gurmukhi: str
    roman: Optional[str]
    source: str
    ang: Optional[int]
    raag: Optional[str]
    author: Optional[str]
    similarity_score: float
    similarity_type: str  # "similar" or "dissimilar"
    shared_keywords: List[str]  # Keywords shared with query


@dataclass
class PramanSearchResult:
    """Combined result of similar and dissimilar praman searches."""
    query_text: str
    similar_pramans: List[PramanResult]
    dissimilar_pramans: List[PramanResult]
    query_keywords: List[str]


class SemanticPramanService:
    """
    Service for finding semantically related pramans from scripture.
    
    Uses sentence-transformers for semantic embeddings and FAISS for
    efficient similarity search. Combines semantic similarity with
    keyword overlap for comprehensive results.
    """
    
    # High-frequency Gurbani keywords for vocabulary matching
    GURBANI_KEYWORDS = {
        # Divine names
        'ਹਰਿ', 'ਪ੍ਰਭ', 'ਪ੍ਰਭੁ', 'ਗੋਬਿੰਦ', 'ਗੋਪਾਲ', 'ਰਾਮ', 'ਵਾਹਿਗੁਰੂ',
        'ਨਾਰਾਇਣ', 'ਮਾਧੋ', 'ਮੁਰਾਰਿ', 'ਠਾਕੁਰ', 'ਸਾਹਿਬ',
        # Core concepts
        'ਨਾਮ', 'ਨਾਮੁ', 'ਸਬਦ', 'ਸਬਦੁ', 'ਹੁਕਮ', 'ਹੁਕਮੁ', 'ਗੁਰ', 'ਗੁਰੁ',
        'ਸਤਿਗੁਰ', 'ਸਤਿਗੁਰੁ', 'ਬਾਣੀ', 'ਗੁਰਬਾਣੀ',
        # Spiritual states
        'ਮੁਕਤਿ', 'ਮੋਖ', 'ਨਿਰਵਾਣ', 'ਅਨੰਦ', 'ਸੁਖ', 'ਦੁਖ', 'ਸਾਂਤਿ',
        'ਭਗਤਿ', 'ਪ੍ਰੇਮ', 'ਪਿਆਰ', 'ਸੇਵਾ', 'ਸਿਮਰਨ',
        # Human conditions
        'ਮਨ', 'ਮਨੁ', 'ਤਨ', 'ਤਨੁ', 'ਹਿਰਦਾ', 'ਆਤਮਾ', 'ਜੀਉ',
        'ਹਉਮੈ', 'ਅਹੰਕਾਰ', 'ਮਾਇਆ', 'ਮੋਹ', 'ਲੋਭ', 'ਕਾਮ', 'ਕ੍ਰੋਧ',
        # Actions and practices
        'ਜਪ', 'ਜਪੁ', 'ਤਪ', 'ਤਪੁ', 'ਦਾਨ', 'ਦਾਨੁ', 'ਇਸਨਾਨ', 'ਪੂਜਾ',
        'ਧਿਆਨ', 'ਧਿਆਨੁ', 'ਸੁਣ', 'ਸੁਣਿ', 'ਮੰਨ', 'ਮੰਨਿ',
        # Creation/nature
        'ਸ੍ਰਿਸ਼ਟਿ', 'ਜਗਤ', 'ਸੰਸਾਰ', 'ਧਰਤੀ', 'ਆਕਾਸ਼', 'ਪਾਣੀ',
        'ਪਵਨ', 'ਅਗਨਿ', 'ਸੂਰਜ', 'ਚੰਦ',
        # Relationships
        'ਪਿਤਾ', 'ਮਾਤਾ', 'ਪੁਤ੍ਰ', 'ਭਾਈ', 'ਸਖੀ', 'ਸੰਗਤ', 'ਸਾਧ',
        # Time/life
        'ਜਨਮ', 'ਮਰਣ', 'ਮੌਤ', 'ਜੀਵਨ', 'ਕਰਮ', 'ਧਰਮ',
    }
    
    # Thematic categories for dissimilarity detection
    THEME_CATEGORIES = {
        'divine_praise': {'ਹਰਿ', 'ਪ੍ਰਭ', 'ਗੋਬਿੰਦ', 'ਵਾਹਿਗੁਰੂ', 'ਸਿਫਤਿ', 'ਸਾਲਾਹ'},
        'human_suffering': {'ਦੁਖ', 'ਕਸ਼ਟ', 'ਪੀੜ', 'ਰੋਗ', 'ਭਉ', 'ਡਰ'},
        'liberation': {'ਮੁਕਤਿ', 'ਮੋਖ', 'ਤਰਣ', 'ਉਧਾਰ', 'ਨਿਰਵਾਣ'},
        'worldly_attachment': {'ਮਾਇਆ', 'ਮੋਹ', 'ਲੋਭ', 'ਅਹੰਕਾਰ', 'ਹਉਮੈ'},
        'devotion': {'ਭਗਤਿ', 'ਪ੍ਰੇਮ', 'ਸੇਵਾ', 'ਸਿਮਰਨ', 'ਜਪ'},
        'guru_grace': {'ਗੁਰ', 'ਸਤਿਗੁਰ', 'ਕਿਰਪਾ', 'ਮਿਹਰ', 'ਨਦਰਿ'},
    }
    
    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        index_path: Optional[Path] = None,
        cache_embeddings: bool = True
    ):
        """
        Initialize semantic praman service.
        
        Args:
            model_name: Sentence transformer model name
            index_path: Path to pre-built FAISS index
            cache_embeddings: Whether to cache embeddings for faster queries
        """
        self.model_name = model_name
        self.index_path = index_path
        self.cache_embeddings = cache_embeddings
        
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional['faiss.Index'] = None
        self.line_data: Dict[int, Dict] = {}  # Index position -> line metadata
        self.embedding_cache: Dict[str, np.ndarray] = {}
        
        self._initialized = False
        
        if index_path and index_path.exists():
            self._load_index(index_path)
    
    def _ensure_initialized(self) -> bool:
        """Ensure the service is initialized with required dependencies."""
        if self._initialized:
            return True
        
        if not NUMPY_AVAILABLE:
            logger.error("numpy required for semantic praman service")
            return False
        
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers required for semantic praman service")
            return False
        
        if not FAISS_AVAILABLE:
            logger.error("faiss required for semantic praman service")
            return False
        
        # Load model if not loaded
        if self.model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
        
        self._initialized = True
        return True
    
    def build_index(
        self,
        sggs_db=None,
        dasam_db=None,
        max_lines: Optional[int] = None
    ) -> bool:
        """
        Build FAISS index from scripture databases.
        
        Args:
            sggs_db: SGGS database instance
            dasam_db: Dasam Granth database instance
            max_lines: Maximum lines to index (None = all)
        
        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_initialized():
            return False
        
        logger.info("Building semantic praman index...")
        
        all_lines = []
        
        # Load SGGS lines
        if sggs_db:
            try:
                cursor = sggs_db._connection.execute(
                    "SELECT id, gurmukhi, source_page FROM lines LIMIT ?",
                    (max_lines or 100000,)
                )
                for row in cursor.fetchall():
                    line = sggs_db.get_line_by_id(str(row['id']))
                    if line and line.gurmukhi and len(line.gurmukhi.strip()) > 5:
                        all_lines.append({
                            'line_id': line.line_id,
                            'gurmukhi': line.gurmukhi,
                            'roman': line.roman,
                            'source': 'SGGS',
                            'ang': line.ang,
                            'raag': line.raag,
                            'author': line.author,
                            'shabad_id': line.shabad_id
                        })
                logger.info(f"Loaded {len(all_lines)} lines from SGGS")
            except Exception as e:
                logger.warning(f"Failed to load SGGS lines: {e}")
        
        # Load Dasam Granth lines
        if dasam_db and hasattr(dasam_db, '_connection') and dasam_db._connection:
            try:
                cursor = dasam_db._connection.execute(
                    "SELECT id FROM lines LIMIT ?",
                    (max_lines or 100000,)
                )
                dasam_count = 0
                for row in cursor.fetchall():
                    line = dasam_db.get_line_by_id(str(row['id']))
                    if line and line.gurmukhi and len(line.gurmukhi.strip()) > 5:
                        all_lines.append({
                            'line_id': line.line_id,
                            'gurmukhi': line.gurmukhi,
                            'roman': line.roman,
                            'source': 'Dasam Granth',
                            'ang': line.ang,
                            'raag': line.raag,
                            'author': line.author,
                            'shabad_id': getattr(line, 'shabad_id', None)
                        })
                        dasam_count += 1
                logger.info(f"Loaded {dasam_count} lines from Dasam Granth")
            except Exception as e:
                logger.warning(f"Failed to load Dasam Granth lines: {e}")
        
        if not all_lines:
            logger.warning("No lines found to index")
            return False
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(all_lines)} lines...")
        texts = [line['gurmukhi'] for line in all_lines]
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # Normalize for cosine similarity
        )
        
        # Create FAISS index (using Inner Product for normalized vectors = cosine similarity)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings.astype('float32'))
        
        # Store line metadata
        self.line_data = {i: line for i, line in enumerate(all_lines)}
        
        logger.info(f"Built semantic index with {len(all_lines)} lines, dimension {dimension}")
        
        # Save index if path provided
        if self.index_path:
            self._save_index(self.index_path)
        
        return True
    
    def _save_index(self, path: Path) -> None:
        """Save index and metadata to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(path))
        
        # Save metadata
        metadata_path = path.with_suffix('.meta.pkl')
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'line_data': self.line_data,
                'model_name': self.model_name
            }, f)
        
        logger.info(f"Saved semantic index to {path}")
    
    def _load_index(self, path: Path) -> bool:
        """Load index and metadata from disk."""
        if not path.exists():
            logger.warning(f"Index file not found: {path}")
            return False
        
        try:
            if not self._ensure_initialized():
                return False
            
            # Load FAISS index
            self.index = faiss.read_index(str(path))
            
            # Load metadata
            metadata_path = path.with_suffix('.meta.pkl')
            if metadata_path.exists():
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    self.line_data = metadata.get('line_data', {})
                    saved_model = metadata.get('model_name')
                    if saved_model and saved_model != self.model_name:
                        logger.warning(
                            f"Model mismatch: index built with {saved_model}, "
                            f"but using {self.model_name}"
                        )
            
            logger.info(f"Loaded semantic index from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
    
    def _get_embedding(self, text: str) -> Optional['np.ndarray']:
        """Get embedding for text, using cache if available."""
        if not self._ensure_initialized():
            return None
        
        # Check cache
        if self.cache_embeddings and text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # Generate embedding
        embedding = self.model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True
        ).astype('float32')
        
        # Cache it
        if self.cache_embeddings:
            self.embedding_cache[text] = embedding
        
        return embedding
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract Gurbani keywords from text."""
        words = set(re.findall(r'[\u0A00-\u0A7F]+', text))
        return words.intersection(self.GURBANI_KEYWORDS)
    
    def _identify_themes(self, text: str) -> Set[str]:
        """Identify thematic categories in text."""
        words = set(re.findall(r'[\u0A00-\u0A7F]+', text))
        themes = set()
        
        for theme, keywords in self.THEME_CATEGORIES.items():
            if words.intersection(keywords):
                themes.add(theme)
        
        return themes
    
    def find_similar_pramans(
        self,
        query_text: str,
        top_k: int = 5,
        exclude_line_ids: Optional[Set[str]] = None
    ) -> List[PramanResult]:
        """
        Find pramans semantically similar to query text.
        
        Args:
            query_text: Query text (Gurmukhi)
            top_k: Number of results to return
            exclude_line_ids: Line IDs to exclude from results
        
        Returns:
            List of PramanResult ordered by similarity
        """
        if not self._ensure_initialized() or self.index is None:
            logger.warning("Semantic index not initialized")
            return []
        
        exclude_line_ids = exclude_line_ids or set()
        query_keywords = self._extract_keywords(query_text)
        
        # Get query embedding
        query_embedding = self._get_embedding(query_text)
        if query_embedding is None:
            return []
        
        # Search for more results to filter
        search_k = min(top_k * 3, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, search_k)
        
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx not in self.line_data:
                continue
            
            line = self.line_data[idx]
            
            # Skip excluded lines
            if line['line_id'] in exclude_line_ids:
                continue
            
            # Calculate keyword overlap
            line_keywords = self._extract_keywords(line['gurmukhi'])
            shared_keywords = list(query_keywords.intersection(line_keywords))
            
            # Boost score based on keyword overlap
            keyword_boost = len(shared_keywords) * 0.05
            adjusted_score = float(score) + keyword_boost
            
            results.append(PramanResult(
                line_id=line['line_id'],
                gurmukhi=line['gurmukhi'],
                roman=line.get('roman'),
                source=line['source'],
                ang=line.get('ang'),
                raag=line.get('raag'),
                author=line.get('author'),
                similarity_score=min(1.0, adjusted_score),
                similarity_type='similar',
                shared_keywords=shared_keywords
            ))
            
            if len(results) >= top_k:
                break
        
        return results
    
    def find_dissimilar_pramans(
        self,
        query_text: str,
        top_k: int = 5,
        exclude_line_ids: Optional[Set[str]] = None,
        contrast_threshold: float = 0.3
    ) -> List[PramanResult]:
        """
        Find pramans that present contrasting/opposite themes.
        
        Uses thematic analysis to find verses with different themes
        but still relevant to the spiritual context.
        
        Args:
            query_text: Query text (Gurmukhi)
            top_k: Number of results to return
            exclude_line_ids: Line IDs to exclude
            contrast_threshold: Maximum similarity to consider dissimilar
        
        Returns:
            List of PramanResult with contrasting themes
        """
        if not self._ensure_initialized() or self.index is None:
            logger.warning("Semantic index not initialized")
            return []
        
        exclude_line_ids = exclude_line_ids or set()
        query_themes = self._identify_themes(query_text)
        query_keywords = self._extract_keywords(query_text)
        
        # Define contrasting theme pairs
        theme_contrasts = {
            'divine_praise': 'human_suffering',
            'human_suffering': 'liberation',
            'liberation': 'worldly_attachment',
            'worldly_attachment': 'devotion',
            'devotion': 'worldly_attachment',
            'guru_grace': 'human_suffering',
        }
        
        # Find contrasting themes
        target_themes = set()
        for theme in query_themes:
            if theme in theme_contrasts:
                target_themes.add(theme_contrasts[theme])
        
        # If no specific themes identified, search broadly
        if not target_themes:
            target_themes = set(self.THEME_CATEGORIES.keys()) - query_themes
        
        # Get query embedding for filtering
        query_embedding = self._get_embedding(query_text)
        if query_embedding is None:
            return []
        
        # Search all lines for thematic contrast
        search_k = min(self.index.ntotal, 1000)
        scores, indices = self.index.search(query_embedding, search_k)
        
        candidates = []
        for idx, score in zip(indices[0], scores[0]):
            if idx < 0 or idx not in self.line_data:
                continue
            
            line = self.line_data[idx]
            
            # Skip excluded lines
            if line['line_id'] in exclude_line_ids:
                continue
            
            # Skip very similar lines
            if float(score) > (1.0 - contrast_threshold):
                continue
            
            # Check for thematic contrast
            line_themes = self._identify_themes(line['gurmukhi'])
            if line_themes.intersection(target_themes):
                line_keywords = self._extract_keywords(line['gurmukhi'])
                shared_keywords = list(query_keywords.intersection(line_keywords))
                
                # Dissimilarity score (inverse of similarity)
                dissimilarity = 1.0 - float(score)
                
                candidates.append(PramanResult(
                    line_id=line['line_id'],
                    gurmukhi=line['gurmukhi'],
                    roman=line.get('roman'),
                    source=line['source'],
                    ang=line.get('ang'),
                    raag=line.get('raag'),
                    author=line.get('author'),
                    similarity_score=dissimilarity,
                    similarity_type='dissimilar',
                    shared_keywords=shared_keywords
                ))
        
        # Sort by dissimilarity and return top_k
        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        return candidates[:top_k]
    
    def search_pramans(
        self,
        query_text: str,
        similar_count: int = 5,
        dissimilar_count: int = 3,
        exclude_same_shabad: bool = True,
        current_shabad_id: Optional[str] = None
    ) -> PramanSearchResult:
        """
        Search for both similar and dissimilar pramans.
        
        Args:
            query_text: Query text (Gurmukhi)
            similar_count: Number of similar pramans
            dissimilar_count: Number of dissimilar pramans
            exclude_same_shabad: Exclude lines from the same shabad
            current_shabad_id: Current shabad ID for exclusion
        
        Returns:
            PramanSearchResult with both similar and dissimilar results
        """
        exclude_ids = set()
        
        # Build exclusion set for same shabad
        if exclude_same_shabad and current_shabad_id:
            for idx, line in self.line_data.items():
                if line.get('shabad_id') == current_shabad_id:
                    exclude_ids.add(line['line_id'])
        
        # Find similar pramans
        similar = self.find_similar_pramans(
            query_text,
            top_k=similar_count,
            exclude_line_ids=exclude_ids
        )
        
        # Add found line_ids to exclusion
        for praman in similar:
            exclude_ids.add(praman.line_id)
        
        # Find dissimilar pramans
        dissimilar = self.find_dissimilar_pramans(
            query_text,
            top_k=dissimilar_count,
            exclude_line_ids=exclude_ids
        )
        
        query_keywords = list(self._extract_keywords(query_text))
        
        return PramanSearchResult(
            query_text=query_text,
            similar_pramans=similar,
            dissimilar_pramans=dissimilar,
            query_keywords=query_keywords
        )


# Singleton instance
_semantic_praman_service: Optional[SemanticPramanService] = None


def get_semantic_praman_service(
    index_path: Optional[Path] = None
) -> SemanticPramanService:
    """
    Get singleton semantic praman service instance.
    
    Args:
        index_path: Path to pre-built index
    
    Returns:
        SemanticPramanService instance
    """
    global _semantic_praman_service
    
    if _semantic_praman_service is None:
        import config
        default_path = getattr(config, 'SEMANTIC_INDEX_PATH', None)
        path = index_path or default_path
        
        _semantic_praman_service = SemanticPramanService(
            model_name=getattr(
                config,
                'EMBEDDING_MODEL_SEMANTIC',
                'paraphrase-multilingual-MiniLM-L12-v2'
            ),
            index_path=path
        )
    
    return _semantic_praman_service

