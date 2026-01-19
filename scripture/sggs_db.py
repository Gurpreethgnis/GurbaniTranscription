"""
ShabadOS SGGS (Sri Guru Granth Sahib Ji) Database Connector.

Provides access to the ShabadOS SQLite database for searching and retrieving
canonical Gurbani text with metadata.
"""
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from models import ScriptureLine, ScriptureSource
from errors import DatabaseNotFoundError
from scripture.gurmukhi_to_ascii import try_ascii_search
import config

logger = logging.getLogger(__name__)


class SGGSDatabase:
    """
    Connector for ShabadOS SGGS SQLite database.
    
    Provides methods to search and retrieve lines from Sri Guru Granth Sahib Ji
    with full metadata (Ang, Raag, Author, etc.).
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize SGGS database connector.
        
        Args:
            db_path: Path to ShabadOS SQLite database file.
                    Defaults to config.SCRIPTURE_DB_PATH
        
        Raises:
            DatabaseNotFoundError: If database file does not exist
        """
        self.db_path = db_path or config.SCRIPTURE_DB_PATH
        if not self.db_path.exists():
            raise DatabaseNotFoundError(
                str(self.db_path),
                "SGGS"
            )
        
        logger.info(f"Initializing SGGS database connector: {self.db_path}")
        self._connection: Optional[sqlite3.Connection] = None
        self._ensure_connection()
    
    def _ensure_connection(self) -> None:
        """Ensure database connection is open."""
        if self._connection is None:
            try:
                self._connection = sqlite3.connect(str(self.db_path))
                self._connection.row_factory = sqlite3.Row  # Enable column access by name
                logger.debug("SGGS database connection established")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to SGGS database: {e}")
                raise DatabaseNotFoundError(
                    str(self.db_path),
                    "SGGS"
                ) from e
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("SGGS database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _get_table_names(self) -> List[str]:
        """Get list of table names in the database."""
        self._ensure_connection()
        cursor = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        return [row[0] for row in cursor.fetchall()]
    
    def search_by_text(
        self,
        text: str,
        top_k: int = 10,
        fuzzy: bool = True
    ) -> List[ScriptureLine]:
        """
        Search for lines containing the given text.
        
        Args:
            text: Text to search for (Gurmukhi)
            top_k: Maximum number of results to return
            fuzzy: If True, use LIKE pattern matching; if False, exact match
        
        Returns:
            List of ScriptureLine objects matching the search
        """
        self._ensure_connection()
        
        if not text or not text.strip():
            logger.warning("Empty search text provided")
            return []
        
        # Convert Unicode Gurmukhi to ASCII transliteration if needed
        # ShabadOS database uses ASCII transliteration format
        search_text = try_ascii_search(text)
        logger.debug(f"Search text (original: '{text[:50]}', converted: '{search_text[:50]}')")
        
        # Try different table structures (ShabadOS may have different schemas)
        # Common table names: lines, shabads, gurbani_lines, etc.
        table_names = self._get_table_names()
        
        # Look for common table names (ShabadOS uses 'lines' table)
        lines_table = None
        for name in ['lines', 'gurbani_lines', 'shabads', 'line']:
            if name in table_names:
                lines_table = name
                break
        
        if not lines_table:
            logger.warning(f"Could not find lines table. Available tables: {table_names}")
            # Try to use the first table that looks like it might contain text
            for name in table_names:
                if 'line' in name.lower() or 'shabad' in name.lower() or 'gurbani' in name.lower():
                    lines_table = name
                    break
        
        if not lines_table:
            logger.error(f"No suitable table found in database. Tables: {table_names}")
            return []
        
        logger.debug(f"Using table: {lines_table}")
        
        # Try to find text column (ShabadOS uses 'gurmukhi' column)
        # First, get column names
        cursor = self._connection.execute(f"PRAGMA table_info({lines_table})")
        columns = [row[1] for row in cursor.fetchall()]
        
        text_column = None
        for col in ['gurmukhi', 'text', 'line', 'gurbani', 'line_text']:
            if col in columns:
                text_column = col
                break
        
        if not text_column:
            logger.warning(f"Could not find text column. Available columns: {columns}")
            # Use first column as fallback
            if columns:
                text_column = columns[0]
            else:
                return []
        
        logger.debug(f"Using text column: {text_column}")
        
        # Build query with JOIN to get metadata (raag, author) from shabads table
        # and transliteration from transliterations table
        # ShabadOS schema: lines table has shabad_id, shabads table has writer_id, section_id
        # transliterations table has line_id and language_id (1 = English/Roman)
        has_transliterations = 'transliterations' in table_names
        
        if 'shabads' in table_names:
            # Use JOIN to get writer, section info, and transliteration
            if has_transliterations:
                if fuzzy:
                    query = f"""
                        SELECT l.*, s.writer_id, s.section_id, t.transliteration as roman
                        FROM {lines_table} l
                        LEFT JOIN shabads s ON l.shabad_id = s.id
                        LEFT JOIN transliterations t ON l.id = t.line_id AND t.language_id = 1
                        WHERE l.{text_column} LIKE ?
                        LIMIT ?
                    """
                    search_pattern = f"%{search_text}%"
                    params = (search_pattern, top_k)
                else:
                    query = f"""
                        SELECT l.*, s.writer_id, s.section_id, t.transliteration as roman
                        FROM {lines_table} l
                        LEFT JOIN shabads s ON l.shabad_id = s.id
                        LEFT JOIN transliterations t ON l.id = t.line_id AND t.language_id = 1
                        WHERE l.{text_column} = ?
                        LIMIT ?
                    """
                    params = (search_text, top_k)
            else:
                # No transliterations table, use original query
                if fuzzy:
                    query = f"""
                        SELECT l.*, s.writer_id, s.section_id
                        FROM {lines_table} l
                        LEFT JOIN shabads s ON l.shabad_id = s.id
                        WHERE l.{text_column} LIKE ?
                        LIMIT ?
                    """
                    search_pattern = f"%{search_text}%"
                    params = (search_pattern, top_k)
                else:
                    query = f"""
                        SELECT l.*, s.writer_id, s.section_id
                        FROM {lines_table} l
                        LEFT JOIN shabads s ON l.shabad_id = s.id
                        WHERE l.{text_column} = ?
                        LIMIT ?
                    """
                    params = (search_text, top_k)
        else:
            # No shabads table
            if has_transliterations:
                if fuzzy:
                    query = f"""
                        SELECT l.*, t.transliteration as roman
                        FROM {lines_table} l
                        LEFT JOIN transliterations t ON l.id = t.line_id AND t.language_id = 1
                        WHERE l.{text_column} LIKE ?
                        LIMIT ?
                    """
                    search_pattern = f"%{search_text}%"
                    params = (search_pattern, top_k)
                else:
                    query = f"""
                        SELECT l.*, t.transliteration as roman
                        FROM {lines_table} l
                        LEFT JOIN transliterations t ON l.id = t.line_id AND t.language_id = 1
                        WHERE l.{text_column} = ?
                        LIMIT ?
                    """
                    params = (search_text, top_k)
            else:
                # No transliterations table, use simple query
                if fuzzy:
                    query = f"""
                        SELECT * FROM {lines_table}
                        WHERE {text_column} LIKE ?
                        LIMIT ?
                    """
                    search_pattern = f"%{search_text}%"
                    params = (search_pattern, top_k)
                else:
                    query = f"""
                        SELECT * FROM {lines_table}
                        WHERE {text_column} = ?
                        LIMIT ?
                    """
                    params = (search_text, top_k)
        
        try:
            cursor = self._connection.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                # Try to extract common fields
                # sqlite3.Row supports dictionary-like access with [] or .keys()
                row_keys = row.keys()
                line_id = str(row['id'] if 'id' in row_keys else (row['line_id'] if 'line_id' in row_keys else ''))
                gurmukhi = str(row[text_column] if text_column in row_keys else (row['gurmukhi'] if 'gurmukhi' in row_keys else ''))
                
                # ShabadOS schema: lines table has 'source_page' for Ang
                ang = None
                for key in ['source_page', 'ang', 'page', 'page_number']:
                    if key in row_keys:
                        try:
                            ang = int(row[key]) if row[key] is not None else None
                            break
                        except (ValueError, TypeError):
                            continue
                
                # ShabadOS: raag/author come from shabads table via JOIN
                # For now, we get writer_id and section_id, but would need additional
                # queries to get actual names - leaving as None for now
                # TODO: Add queries to writers and sections tables to get names
                raag = None
                for key in ['raag', 'raag_name', 'section_id']:
                    if key in row_keys and row[key] is not None:
                        # section_id is not raag name, but we'll store it for now
                        raag = str(row[key])
                        break
                
                author = None
                for key in ['author', 'writer', 'writer_name', 'writer_id']:
                    if key in row_keys and row[key] is not None:
                        # writer_id is not author name, but we'll store it for now
                        author = str(row[key])
                        break
                
                # ShabadOS has transliterations in separate table (now joined)
                roman = None
                for key in ['roman', 'transliteration', 'pronunciation']:
                    if key in row_keys and row[key] is not None:
                        roman = str(row[key]).strip()
                        if roman:  # Only use if not empty
                            break
                
                # ShabadOS schema: lines table has 'shabad_id'
                shabad_id = None
                for key in ['shabad_id', 'shabad']:
                    if key in row_keys and row[key] is not None:
                        shabad_id = row[key]
                        break
                
                scripture_line = ScriptureLine(
                    line_id=line_id,
                    gurmukhi=gurmukhi,
                    roman=roman if roman else None,
                    source=ScriptureSource.SGGS,
                    ang=ang if ang is not None else None,
                    raag=raag if raag else None,
                    author=author if author else None,
                    shabad_id=str(shabad_id) if shabad_id else None
                )
                results.append(scripture_line)
            
            logger.debug(f"Found {len(results)} matching lines for text: {text[:50]}")
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Database error during search: {e}")
            return []
    
    def get_line_by_id(self, line_id: str) -> Optional[ScriptureLine]:
        """
        Get a specific line by its ID.
        
        Args:
            line_id: Line identifier
        
        Returns:
            ScriptureLine if found, None otherwise
        """
        self._ensure_connection()
        
        table_names = self._get_table_names()
        has_transliterations = 'transliterations' in table_names
        
        # Find the lines table
        lines_table = None
        for name in ['lines', 'gurbani_lines', 'shabads', 'line']:
            if name in table_names:
                lines_table = name
                break
        
        if not lines_table:
            logger.warning(f"Could not find lines table for line_id: {line_id}")
            return None
        
        # Build query with JOIN to transliterations if available
        if has_transliterations:
            query = f"""
                SELECT l.*, t.transliteration as roman
                FROM {lines_table} l
                LEFT JOIN transliterations t ON l.id = t.line_id AND t.language_id = 1
                WHERE l.id = ?
            """
        else:
            query = f"""
                SELECT * FROM {lines_table}
                WHERE id = ?
            """
        
        try:
            cursor = self._connection.execute(query, (line_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Line not found: {line_id}")
                return None
            
            row_keys = row.keys()
            
            # Find text column
            text_column = None
            for col in ['gurmukhi', 'text', 'line', 'gurbani']:
                if col in row_keys:
                    text_column = col
                    break
            
            if not text_column:
                logger.warning(f"Could not find text column for line_id: {line_id}")
                return None
            
            gurmukhi = str(row[text_column])
            
            # ShabadOS uses 'source_page' for Ang
            ang = None
            for key in ['source_page', 'ang', 'page', 'page_number']:
                if key in row_keys:
                    try:
                        ang = int(row[key]) if row[key] is not None else None
                        break
                    except (ValueError, TypeError):
                        continue
            
            # Get transliteration (from JOIN or direct column)
            roman = None
            if 'roman' in row_keys and row['roman'] is not None:
                roman = str(row['roman']).strip()
            
            # Get raag
            raag = None
            for key in ['raag', 'raag_name']:
                if key in row_keys and row[key] is not None:
                    raag = str(row[key])
                    break
            
            # Get author
            author = None
            for key in ['author', 'writer', 'writer_name']:
                if key in row_keys and row[key] is not None:
                    author = str(row[key])
                    break
            
            # Try to get writer name if we have writer_id
            if 'writer_id' in row_keys and row['writer_id'] is not None:
                try:
                    writer_cursor = self._connection.execute(
                        "SELECT name_english FROM writers WHERE id = ?",
                        (row['writer_id'],)
                    )
                    writer_row = writer_cursor.fetchone()
                    if writer_row:
                        author = writer_row['name_english']
                except sqlite3.Error:
                    pass  # Keep author as writer_id if lookup fails
            
            # Get shabad_id
            shabad_id = None
            for key in ['shabad_id', 'shabad']:
                if key in row_keys and row[key] is not None:
                    shabad_id = row[key]
                    break
            
            return ScriptureLine(
                line_id=line_id,
                gurmukhi=gurmukhi,
                roman=roman if roman else None,
                source=ScriptureSource.SGGS,
                ang=ang,
                raag=raag,
                author=author,
                shabad_id=str(shabad_id) if shabad_id else None
            )
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting line by ID: {e}")
            return None
    
    def get_context(
        self,
        line_id: str,
        window: int = 2
    ) -> List[ScriptureLine]:
        """
        Get surrounding context lines for a given line.
        
        Args:
            line_id: Line identifier
            window: Number of lines before and after to retrieve
        
        Returns:
            List of ScriptureLine objects (context lines)
        """
        # For now, return just the line itself
        # Full implementation would require understanding the database ordering
        line = self.get_line_by_id(line_id)
        if line:
            return [line]
        return []
