"""
Unified Scripture Service API.

Provides a single interface for accessing all scripture sources
(SGGS, Dasam Granth, etc.) for quote matching and canonical text retrieval.
"""
import logging
from typing import List, Optional
from models import ScriptureLine, ScriptureSource
from scripture.sggs_db import SGGSDatabase
from scripture.dasam_db import DasamDatabase
from errors import DatabaseNotFoundError

logger = logging.getLogger(__name__)


class ScriptureService:
    """
    Unified service for accessing all scripture databases.
    
    Provides a single API for searching and retrieving canonical text
    from multiple sources (SGGS, Dasam Granth, etc.).
    """
    
    def __init__(
        self,
        sggs_db: Optional[SGGSDatabase] = None,
        dasam_db: Optional[DasamDatabase] = None
    ):
        """
        Initialize scripture service.
        
        Args:
            sggs_db: SGGS database connector (created if None)
            dasam_db: Dasam Granth database connector (created if None)
        """
        # Initialize SGGS database (required)
        try:
            self.sggs_db = sggs_db or SGGSDatabase()
            logger.info("SGGS database initialized")
        except DatabaseNotFoundError as e:
            logger.warning(f"SGGS database not available: {e}")
            self.sggs_db = None
        
        # Initialize Dasam Granth database (optional)
        try:
            self.dasam_db = dasam_db or DasamDatabase()
            logger.info("Dasam Granth database initialized")
        except DatabaseNotFoundError as e:
            logger.warning(f"Dasam Granth database not available: {e}")
            self.dasam_db = None
    
    def search_candidates(
        self,
        text: str,
        source: Optional[ScriptureSource] = None,
        top_k: int = 10,
        fuzzy: bool = True
    ) -> List[ScriptureLine]:
        """
        Search for scripture lines matching the given text.
        
        Args:
            text: Text to search for (Gurmukhi)
            source: Optional source to search (None = search all sources)
            top_k: Maximum number of results per source
            fuzzy: If True, use fuzzy matching; if False, exact match
        
        Returns:
            List of ScriptureLine objects from matching sources
        """
        if not text or not text.strip():
            logger.warning("Empty search text provided")
            return []
        
        results: List[ScriptureLine] = []
        
        # Search SGGS if requested or if source is None
        if (source is None or source == ScriptureSource.SGGS) and self.sggs_db:
            try:
                sggs_results = self.sggs_db.search_by_text(text, top_k, fuzzy)
                results.extend(sggs_results)
                logger.debug(f"Found {len(sggs_results)} matches in SGGS")
            except Exception as e:
                logger.error(f"Error searching SGGS: {e}")
        
        # Search Dasam Granth if requested or if source is None
        if (source is None or source == ScriptureSource.DasamGranth) and self.dasam_db:
            try:
                dasam_results = self.dasam_db.search_by_text(text, top_k, fuzzy)
                results.extend(dasam_results)
                logger.debug(f"Found {len(dasam_results)} matches in Dasam Granth")
            except Exception as e:
                logger.error(f"Error searching Dasam Granth: {e}")
        
        logger.info(f"Total matches found: {len(results)}")
        return results
    
    def get_canonical(self, line_id: str, source: ScriptureSource) -> Optional[ScriptureLine]:
        """
        Get canonical text for a specific line.
        
        Args:
            line_id: Line identifier
            source: Scripture source
        
        Returns:
            ScriptureLine if found, None otherwise
        """
        if source == ScriptureSource.SGGS and self.sggs_db:
            return self.sggs_db.get_line_by_id(line_id)
        elif source == ScriptureSource.DasamGranth and self.dasam_db:
            return self.dasam_db.get_line_by_id(line_id)
        else:
            logger.warning(f"Source {source} not available or not supported")
            return None
    
    def get_line_context(
        self,
        line_id: str,
        source: ScriptureSource,
        window: int = 2
    ) -> List[ScriptureLine]:
        """
        Get surrounding context lines for a given line.
        
        Args:
            line_id: Line identifier
            source: Scripture source
            window: Number of lines before and after to retrieve
        
        Returns:
            List of ScriptureLine objects (context lines)
        """
        if source == ScriptureSource.SGGS and self.sggs_db:
            return self.sggs_db.get_context(line_id, window)
        elif source == ScriptureSource.DasamGranth and self.dasam_db:
            return self.dasam_db.get_context(line_id, window)
        else:
            logger.warning(f"Source {source} not available or not supported")
            return []
    
    def close(self) -> None:
        """Close all database connections."""
        if self.sggs_db:
            self.sggs_db.close()
        if self.dasam_db:
            self.dasam_db.close()
        logger.debug("All scripture database connections closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
