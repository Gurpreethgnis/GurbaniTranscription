"""
Test suite for Phase 4 Milestone 2: Scripture Database Service

Tests the SGGS and Dasam Granth database connectors and unified scripture service.
"""
import pytest
import sqlite3
import tempfile
from pathlib import Path
from models import ScriptureSource, ScriptureLine
from errors import DatabaseNotFoundError
from scripture.sggs_db import SGGSDatabase
from scripture.dasam_db import DasamDatabase
from scripture.scripture_service import ScriptureService


class TestSGGSDatabase:
    """Tests for SGGSDatabase connector."""
    
    def test_sggs_db_raises_error_when_not_found(self):
        """Test that SGGSDatabase raises error when database doesn't exist."""
        with pytest.raises(DatabaseNotFoundError):
            SGGSDatabase(db_path=Path("/nonexistent/sggs.db"))
    
    def test_sggs_db_creates_connection(self):
        """Test that SGGSDatabase can connect to an existing database."""
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            # Create a simple database structure
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    gurmukhi TEXT NOT NULL,
                    roman TEXT,
                    ang INTEGER,
                    raag TEXT,
                    author TEXT
                )
            """)
            conn.execute("""
                INSERT INTO lines (id, gurmukhi, roman, ang, raag, author)
                VALUES ('test_001', 'ਵਾਹਿਗੁਰੂ', 'Wahiguru', 1, 'Siri', 'Guru Nanak Dev Ji')
            """)
            conn.commit()
            conn.close()
            
            # Test connection
            db = SGGSDatabase(db_path=db_path)
            assert db.db_path == db_path
            db.close()
        finally:
            if db_path.exists():
                db_path.unlink()
    
    def test_sggs_db_search_by_text(self):
        """Test searching for text in SGGS database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            # Create database with test data
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    gurmukhi TEXT NOT NULL,
                    roman TEXT,
                    ang INTEGER,
                    raag TEXT,
                    author TEXT
                )
            """)
            conn.execute("""
                INSERT INTO lines (id, gurmukhi, roman, ang, raag, author)
                VALUES 
                    ('sggs_001', 'ਵਾਹਿਗੁਰੂ', 'Wahiguru', 1, 'Siri', 'Guru Nanak Dev Ji'),
                    ('sggs_002', 'ਸਤਿਗੁਰੂ', 'Satiguru', 2, 'Majh', 'Guru Angad Dev Ji')
            """)
            conn.commit()
            conn.close()
            
            # Test search
            db = SGGSDatabase(db_path=db_path)
            try:
                results = db.search_by_text("ਵਾਹਿਗੁਰੂ", top_k=5)
                
                assert len(results) > 0
                assert all(isinstance(line, ScriptureLine) for line in results)
                assert any(line.gurmukhi == "ਵਾਹਿਗੁਰੂ" for line in results)
            finally:
                db.close()
                # Wait a bit for file handle to be released on Windows
                import time
                time.sleep(0.1)
        finally:
            if db_path.exists():
                try:
                    db_path.unlink()
                except PermissionError:
                    pass  # File may still be locked, that's okay for tests
    
    def test_sggs_db_get_line_by_id(self):
        """Test retrieving a line by ID."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("""
                CREATE TABLE lines (
                    id TEXT PRIMARY KEY,
                    gurmukhi TEXT NOT NULL
                )
            """)
            conn.execute("""
                INSERT INTO lines (id, gurmukhi)
                VALUES ('test_123', 'ਵਾਹਿਗੁਰੂ')
            """)
            conn.commit()
            conn.close()
            
            db = SGGSDatabase(db_path=db_path)
            try:
                line = db.get_line_by_id("test_123")
                
                assert line is not None
                assert line.line_id == "test_123"
                assert line.gurmukhi == "ਵਾਹਿਗੁਰੂ"
                assert line.source == ScriptureSource.SGGS
            finally:
                db.close()
                import time
                time.sleep(0.1)
        finally:
            if db_path.exists():
                try:
                    db_path.unlink()
                except PermissionError:
                    pass
    
    def test_sggs_db_context_manager(self):
        """Test using SGGSDatabase as context manager."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE lines (id TEXT, gurmukhi TEXT)")
            conn.commit()
            conn.close()
            
            with SGGSDatabase(db_path=db_path) as db:
                assert db._connection is not None
            # Connection should be closed after context exit
        finally:
            if db_path.exists():
                db_path.unlink()


class TestDasamDatabase:
    """Tests for DasamDatabase connector."""
    
    def test_dasam_db_creates_database_if_not_exists(self):
        """Test that DasamDatabase creates database if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "dasam.db"
            
            # Database should not exist yet
            assert not db_path.exists()
            
            # Creating DasamDatabase should create the database
            db = DasamDatabase(db_path=db_path)
            db._ensure_connection()
            
            assert db_path.exists()
            db.close()
    
    def test_dasam_db_search_by_text(self):
        """Test searching for text in Dasam Granth database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "dasam.db"
            
            db = DasamDatabase(db_path=db_path)
            db._ensure_connection()
            
            # Insert test data
            db._connection.execute("""
                INSERT INTO lines (id, gurmukhi, roman, ang)
                VALUES ('dasam_001', 'ਚੰਡੀ', 'Chandi', 1)
            """)
            db._connection.commit()
            
            # Test search
            try:
                results = db.search_by_text("ਚੰਡੀ", top_k=5)
                
                assert len(results) > 0
                assert all(isinstance(line, ScriptureLine) for line in results)
                assert any(line.gurmukhi == "ਚੰਡੀ" for line in results)
                assert all(line.source == ScriptureSource.DasamGranth for line in results)
            finally:
                db.close()
    
    def test_dasam_db_get_line_by_id(self):
        """Test retrieving a line by ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "dasam.db"
            
            db = DasamDatabase(db_path=db_path)
            db._ensure_connection()
            
            db._connection.execute("""
                INSERT INTO lines (id, gurmukhi)
                VALUES ('test_456', 'ਚੰਡੀ')
            """)
            db._connection.commit()
            
            try:
                line = db.get_line_by_id("test_456")
                
                assert line is not None
                assert line.line_id == "test_456"
                assert line.gurmukhi == "ਚੰਡੀ"
                assert line.source == ScriptureSource.DasamGranth
            finally:
                db.close()
    
    def test_dasam_db_context_manager(self):
        """Test using DasamDatabase as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "dasam.db"
            
            with DasamDatabase(db_path=db_path) as db:
                db._ensure_connection()
                assert db._connection is not None
            # Connection should be closed after context exit


class TestScriptureService:
    """Tests for unified ScriptureService."""
    
    def test_scripture_service_initialization(self):
        """Test ScriptureService initialization."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            sggs_path = Path(tmp.name)
        
        try:
            # Create minimal SGGS database
            conn = sqlite3.connect(str(sggs_path))
            conn.execute("CREATE TABLE lines (id TEXT, gurmukhi TEXT)")
            conn.commit()
            conn.close()
            
            sggs_db = SGGSDatabase(db_path=sggs_path)
            service = ScriptureService(sggs_db=sggs_db)
            
            assert service.sggs_db is not None
            # Dasam may not be available, that's okay
            service.close()
        finally:
            if sggs_path.exists():
                sggs_path.unlink()
    
    def test_scripture_service_search_all_sources(self):
        """Test searching across all available sources."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            sggs_path = Path(tmp.name)
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dasam_path = Path(tmpdir) / "dasam.db"
                
                # Create SGGS database
                conn = sqlite3.connect(str(sggs_path))
                conn.execute("""
                    CREATE TABLE lines (id TEXT, gurmukhi TEXT)
                """)
                conn.execute("""
                    INSERT INTO lines (id, gurmukhi)
                    VALUES ('sggs_001', 'ਵਾਹਿਗੁਰੂ')
                """)
                conn.commit()
                conn.close()
                
                # Create Dasam database
                dasam_db = DasamDatabase(db_path=dasam_path)
                dasam_db._ensure_connection()
                dasam_db._connection.execute("""
                    INSERT INTO lines (id, gurmukhi)
                    VALUES ('dasam_001', 'ਚੰਡੀ')
                """)
                dasam_db._connection.commit()
                dasam_db.close()
                
                # Test unified search
                sggs_db = SGGSDatabase(db_path=sggs_path)
                service = ScriptureService(sggs_db=sggs_db, dasam_db=DasamDatabase(db_path=dasam_path))
                
                try:
                    # Search for text that might match either
                    results = service.search_candidates("ਵਾਹਿਗੁਰੂ", top_k=10)
                    
                    assert len(results) > 0
                    # Should find SGGS result
                    assert any(line.source == ScriptureSource.SGGS for line in results)
                finally:
                    service.close()
                    import time
                    time.sleep(0.1)
        finally:
            if sggs_path.exists():
                try:
                    import time
                    time.sleep(0.2)  # Wait for file handles to be released
                    sggs_path.unlink()
                except PermissionError:
                    pass  # File may still be locked, that's okay for tests
    
    def test_scripture_service_get_canonical(self):
        """Test retrieving canonical text."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            sggs_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(sggs_path))
            conn.execute("""
                CREATE TABLE lines (id TEXT, gurmukhi TEXT)
            """)
            conn.execute("""
                INSERT INTO lines (id, gurmukhi)
                VALUES ('canonical_001', 'ਸਤਿਗੁਰੂ')
            """)
            conn.commit()
            conn.close()
            
            sggs_db = SGGSDatabase(db_path=sggs_path)
            service = ScriptureService(sggs_db=sggs_db)
            
            try:
                line = service.get_canonical("canonical_001", ScriptureSource.SGGS)
                
                assert line is not None
                assert line.line_id == "canonical_001"
                assert line.gurmukhi == "ਸਤਿਗੁਰੂ"
            finally:
                service.close()
                import time
                time.sleep(0.1)
        finally:
            if sggs_path.exists():
                try:
                    sggs_path.unlink()
                except PermissionError:
                    pass
    
    def test_scripture_service_context_manager(self):
        """Test using ScriptureService as context manager."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            sggs_path = Path(tmp.name)
        
        try:
            conn = sqlite3.connect(str(sggs_path))
            conn.execute("CREATE TABLE lines (id TEXT, gurmukhi TEXT)")
            conn.commit()
            conn.close()
            
            with ScriptureService(sggs_db=SGGSDatabase(db_path=sggs_path)) as service:
                assert service.sggs_db is not None
            # Connections should be closed after context exit
        finally:
            if sggs_path.exists():
                sggs_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
