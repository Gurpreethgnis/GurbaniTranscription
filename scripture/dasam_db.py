"""
Dasam Granth Database Connector.

Provides access to Dasam Granth database for searching and retrieving
canonical text with metadata.
"""
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional
from models import ScriptureLine, ScriptureSource
from errors import DatabaseNotFoundError
import config

logger = logging.getLogger(__name__)


class DasamDatabase:
    """
    Connector for Dasam Granth SQLite database.
    
    Provides methods to search and retrieve lines from Dasam Granth
    with full metadata.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Dasam Granth database connector.
        
        Args:
            db_path: Path to Dasam Granth SQLite database file.
                    Defaults to config.DASAM_DB_PATH
        
        Raises:
            DatabaseNotFoundError: If database file does not exist
        """
        self.db_path = db_path or config.DASAM_DB_PATH
        if not self.db_path.exists():
            # Dasam database may not exist yet - log warning but don't raise
            logger.warning(f"Dasam Granth database not found at {self.db_path}. "
                         "Database will be created on first use.")
            self._connection: Optional[sqlite3.Connection] = None
        else:
            logger.info(f"Initializing Dasam Granth database connector: {self.db_path}")
            self._connection: Optional[sqlite3.Connection] = None
            self._ensure_connection()
    
    def _ensure_connection(self) -> None:
        """Ensure database connection is open, creating database if needed."""
        if self._connection is None:
            try:
                # Create parent directory if needed
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self._connection = sqlite3.connect(str(self.db_path))
                self._connection.row_factory = sqlite3.Row
                self._create_tables_if_needed()
                logger.debug("Dasam Granth database connection established")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to Dasam Granth database: {e}")
                raise DatabaseNotFoundError(
                    str(self.db_path),
                    "Dasam Granth"
                ) from e
    
    def _create_tables_if_needed(self) -> None:
        """Create database tables if they don't exist."""
        self._ensure_connection()
        
        # Check if tables exist
        cursor = self._connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='lines'"
        )
        if cursor.fetchone():
            return  # Tables already exist
        
        # Create tables
        logger.info("Creating Dasam Granth database schema...")
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS lines (
                id TEXT PRIMARY KEY,
                gurmukhi TEXT NOT NULL,
                roman TEXT,
                ang INTEGER,
                raag TEXT,
                author TEXT,
                shabad_id TEXT
            )
        """)
        
        self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_gurmukhi ON lines(gurmukhi)
        """)
        
        self._connection.commit()
        logger.info("Dasam Granth database schema created")
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Dasam Granth database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
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
        
        if fuzzy:
            query = """
                SELECT * FROM lines
                WHERE gurmukhi LIKE ?
                LIMIT ?
            """
            search_pattern = f"%{text}%"
            params = (search_pattern, top_k)
        else:
            query = """
                SELECT * FROM lines
                WHERE gurmukhi = ?
                LIMIT ?
            """
            params = (text, top_k)
        
        try:
            cursor = self._connection.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                scripture_line = ScriptureLine(
                    line_id=str(row['id']),
                    gurmukhi=str(row['gurmukhi']),
                    roman=row['roman'] if 'roman' in row.keys() and row['roman'] is not None else None,
                    source=ScriptureSource.DasamGranth,
                    ang=row['ang'] if 'ang' in row.keys() and row['ang'] is not None else None,
                    raag=row['raag'] if 'raag' in row.keys() and row['raag'] is not None else None,
                    author=row['author'] if 'author' in row.keys() and row['author'] is not None else None,
                    shabad_id=str(row['shabad_id']) if 'shabad_id' in row.keys() and row['shabad_id'] is not None else None
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
        
        try:
            cursor = self._connection.execute(
                "SELECT * FROM lines WHERE id = ?",
                (line_id,)
            )
            row = cursor.fetchone()
            
            if row:
                row_keys = row.keys()
                return ScriptureLine(
                    line_id=line_id,
                    gurmukhi=str(row['gurmukhi']),
                    roman=row['roman'] if 'roman' in row_keys and row['roman'] is not None else None,
                    source=ScriptureSource.DasamGranth,
                    ang=row['ang'] if 'ang' in row_keys and row['ang'] is not None else None,
                    raag=row['raag'] if 'raag' in row_keys and row['raag'] is not None else None,
                    author=row['author'] if 'author' in row_keys and row['author'] is not None else None,
                    shabad_id=str(row['shabad_id']) if 'shabad_id' in row_keys and row['shabad_id'] is not None else None
                )
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
        
        logger.warning(f"Line not found: {line_id}")
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
            List of ScriptureLine objects (context lines, sorted by order)
        """
        # First, get the current line
        current_line = self.get_line_by_id(line_id)
        if not current_line:
            return []
        
        try:
            # Check if we have an ordering field
            cursor = self._connection.execute("PRAGMA table_info(lines)")
            columns = [col[1] for col in cursor.fetchall()]
            
            order_column = None
            for col_name in ['line_order', 'order', 'sequence', 'line_number', 'id']:
                if col_name in columns:
                    order_column = col_name
                    break
            
            if not order_column:
                # Fallback: use line_id as numeric ordering
                try:
                    current_order = int(line_id.split('_')[-1]) if '_' in line_id else int(line_id)
                except ValueError:
                    return [current_line]
                
                # Query surrounding lines by numeric ID
                context_lines = []
                for offset in range(-window, window + 1):
                    target_id = current_order + offset
                    if target_id >= 0:
                        line = self.get_line_by_id(str(target_id))
                        if line:
                            context_lines.append(line)
                
                return sorted(context_lines, key=lambda l: int(l.line_id.split('_')[-1]) if '_' in l.line_id else int(l.line_id))
            
            # Get current line's order value
            cursor = self._connection.execute(
                f"SELECT {order_column} FROM lines WHERE id = ?",
                (line_id,)
            )
            order_row = cursor.fetchone()
            if not order_row:
                return [current_line]
            
            current_order = order_row[order_column]
            
            # Get shabad_id if available (for filtering)
            shabad_id = None
            if 'shabad_id' in columns:
                cursor = self._connection.execute(
                    "SELECT shabad_id FROM lines WHERE id = ?",
                    (line_id,)
                )
                shabad_row = cursor.fetchone()
                if shabad_row:
                    shabad_id = shabad_row['shabad_id']
            
            # Query surrounding lines
            if shabad_id:
                query = f"""
                    SELECT * FROM lines
                    WHERE shabad_id = ? AND {order_column} >= ? AND {order_column} <= ?
                    ORDER BY {order_column}
                """
                params = (shabad_id, current_order - window, current_order + window)
            else:
                query = f"""
                    SELECT * FROM lines
                    WHERE {order_column} >= ? AND {order_column} <= ?
                    ORDER BY {order_column}
                """
                params = (current_order - window, current_order + window)
            
            cursor = self._connection.execute(query, params)
            context_lines = []
            
            for row in cursor.fetchall():
                # Convert row to ScriptureLine
                line = self._row_to_scripture_line(row)
                if line:
                    context_lines.append(line)
            
            return context_lines if context_lines else [current_line]
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting context for line {line_id}: {e}")
            return [current_line]
    
    def _row_to_scripture_line(self, row: sqlite3.Row) -> Optional[ScriptureLine]:
        """
        Convert a database row to ScriptureLine object.
        
        Args:
            row: Database row
        
        Returns:
            ScriptureLine object, or None if conversion fails
        """
        try:
            line_id = str(row['id'])
            gurmukhi = str(row.get('gurmukhi', ''))
            roman = str(row.get('roman', '')) if row.get('roman') else None
            ang = int(row['ang']) if row.get('ang') is not None else None
            raag = str(row['raag']) if row.get('raag') else None
            author = str(row['author']) if row.get('author') else None
            shabad_id = str(row['shabad_id']) if row.get('shabad_id') else None
            
            return ScriptureLine(
                line_id=line_id,
                gurmukhi=gurmukhi,
                roman=roman,
                source=ScriptureSource.DasamGranth,
                ang=ang,
                raag=raag,
                author=author,
                shabad_id=shabad_id
            )
        except Exception as e:
            logger.debug(f"Failed to convert row to ScriptureLine: {e}")
            return None
