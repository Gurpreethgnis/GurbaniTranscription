"""
Embedding Index Builder for Semantic Search.

Builds FAISS index from scripture lines for semantic quote matching.
"""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import pickle

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logging.warning("numpy not available for embedding index")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("faiss not available. Install with: pip install faiss-cpu or faiss-gpu")

from models import ScriptureLine, ScriptureSource
from scripture.sggs_db import SGGSDatabase
from scripture.dasam_db import DasamDatabase

logger = logging.getLogger(__name__)


class EmbeddingIndex:
    """
    FAISS index for semantic search of scripture lines.
    
    Builds and manages vector embeddings for fast similarity search.
    """
    
    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        index_path: Optional[Path] = None
    ):
        """
        Initialize embedding index.
        
        Args:
            model_name: Sentence transformer model name
            index_path: Path to saved index file (loads if exists)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers required. Install with: pip install sentence-transformers")
        
        if not FAISS_AVAILABLE:
            raise ImportError("faiss required. Install with: pip install faiss-cpu or faiss-gpu")
        
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy required for embedding index")
        
        self.model_name = model_name
        self.index_path = index_path
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.line_id_map: Dict[int, str] = {}  # Index position -> line_id
        self.line_id_to_index: Dict[str, int] = {}  # line_id -> index position
        
        if index_path and index_path.exists():
            self.load_index(index_path)
        else:
            logger.info(f"Embedding index will be built on first use")
    
    def build_index(
        self,
        sggs_db: Optional[SGGSDatabase] = None,
        dasam_db: Optional[DasamDatabase] = None,
        max_lines: Optional[int] = None
    ) -> None:
        """
        Build FAISS index from scripture databases.
        
        Args:
            sggs_db: SGGS database connector
            dasam_db: Dasam Granth database connector
            max_lines: Maximum number of lines to index (None = all)
        """
        logger.info("Building embedding index from scripture databases...")
        
        # Load model
        if self.model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
        
        # Collect all lines
        all_lines: List[ScriptureLine] = []
        
        # Load from SGGS
        if sggs_db:
            try:
                logger.info("Loading lines from SGGS database...")
                # Query all lines (this may be slow for large databases)
                cursor = sggs_db._connection.execute("SELECT id, gurmukhi FROM lines LIMIT ?", (max_lines or 100000,))
                for row in cursor.fetchall():
                    line = sggs_db.get_line_by_id(str(row['id']))
                    if line and line.gurmukhi:
                        all_lines.append(line)
                logger.info(f"Loaded {len(all_lines)} lines from SGGS")
            except Exception as e:
                logger.warning(f"Failed to load SGGS lines: {e}")
        
        # Load from Dasam Granth
        if dasam_db and dasam_db._connection:
            try:
                logger.info("Loading lines from Dasam Granth database...")
                cursor = dasam_db._connection.execute("SELECT id FROM lines LIMIT ?", (max_lines or 100000,))
                dasam_count = 0
                for row in cursor.fetchall():
                    line = dasam_db.get_line_by_id(str(row['id']))
                    if line and line.gurmukhi:
                        all_lines.append(line)
                        dasam_count += 1
                logger.info(f"Loaded {dasam_count} lines from Dasam Granth")
            except Exception as e:
                logger.warning(f"Failed to load Dasam Granth lines: {e}")
        
        if not all_lines:
            logger.warning("No lines found to index")
            return
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(all_lines)} lines...")
        texts = [line.gurmukhi for line in all_lines]
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)  # L2 distance for similarity
        
        # Add embeddings to index
        self.index.add(embeddings.astype('float32'))
        
        # Build line_id mapping
        self.line_id_map = {i: line.line_id for i, line in enumerate(all_lines)}
        self.line_id_to_index = {line.line_id: i for i, line in enumerate(all_lines)}
        
        logger.info(f"Built index with {len(all_lines)} lines, dimension {dimension}")
        
        # Save index if path provided
        if self.index_path:
            self.save_index(self.index_path)
    
    def search(
        self,
        query_text: str,
        top_k: int = 10
    ) -> List[Tuple[ScriptureLine, float]]:
        """
        Search for similar lines using semantic embeddings.
        
        Args:
            query_text: Query text in Gurmukhi
            top_k: Number of results to return
        
        Returns:
            List of (ScriptureLine, similarity_score) tuples
        """
        if self.index is None or self.model is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        # Generate query embedding
        query_embedding = self.model.encode([query_text], convert_to_numpy=True).astype('float32')
        
        # Search in FAISS index
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Convert to ScriptureLine objects
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(self.line_id_map):
                continue
            
            line_id = self.line_id_map[idx]
            # Convert distance to similarity (L2 distance -> similarity)
            # Lower distance = higher similarity
            similarity = 1.0 / (1.0 + distance)
            
            # Note: We don't have direct access to ScriptureLine objects here
            # The caller should retrieve the line using line_id
            results.append((line_id, similarity))
        
        return results
    
    def save_index(self, output_path: Path) -> None:
        """
        Save index to disk.
        
        Args:
            output_path: Path to save index
        """
        if self.index is None:
            raise ValueError("No index to save")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(output_path))
        
        # Save metadata (line_id mappings)
        metadata_path = output_path.with_suffix('.pkl')
        with open(metadata_path, 'wb') as f:
            pickle.dump({
                'line_id_map': self.line_id_map,
                'line_id_to_index': self.line_id_to_index,
                'model_name': self.model_name
            }, f)
        
        logger.info(f"Saved embedding index to {output_path}")
    
    def load_index(self, index_path: Path) -> None:
        """
        Load index from disk.
        
        Args:
            index_path: Path to index file
        """
        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")
        
        # Load FAISS index
        self.index = faiss.read_index(str(index_path))
        
        # Load metadata
        metadata_path = index_path.with_suffix('.pkl')
        if metadata_path.exists():
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
                self.line_id_map = metadata.get('line_id_map', {})
                self.line_id_to_index = metadata.get('line_id_to_index', {})
                self.model_name = metadata.get('model_name', self.model_name)
        
        # Load model
        logger.info(f"Loading sentence transformer model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        
        logger.info(f"Loaded embedding index from {index_path}")
