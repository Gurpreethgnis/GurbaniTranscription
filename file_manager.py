"""
File management utilities for handling uploads, outputs, and logging.
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import config


class FileManager:
    """Manages file operations, logging, and output generation."""
    
    def __init__(self):
        self.log_file = config.LOG_FILE
        self.transcriptions_dir = config.TRANSCRIPTIONS_DIR
        self.json_dir = config.JSON_DIR
        self.upload_dir = config.UPLOAD_DIR
        
        # Ensure directories exist
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.transcriptions_dir.mkdir(parents=True, exist_ok=True)
        self.json_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate MD5 hash of file for duplicate detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def is_file_processed(self, filename: str, file_hash: Optional[str] = None) -> Tuple[bool, Optional[Dict]]:
        """
        Check if a file has already been processed.
        Returns (is_processed, log_entry) tuple.
        """
        log_data = self.load_log()
        
        # Check by filename
        for entry in log_data:
            if entry.get("filename") == filename:
                # If hash provided, verify it matches
                if file_hash and entry.get("file_hash") != file_hash:
                    return False, None
                return True, entry
        
        return False, None
    
    def load_log(self) -> List[Dict]:
        """Load the processing log from JSON file."""
        if not self.log_file.exists():
            return []
        
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def save_log(self, log_data: List[Dict]):
        """Save the processing log to JSON file."""
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    def add_log_entry(
        self,
        filename: str,
        status: str,
        transcription: Optional[str] = None,
        language: Optional[str] = None,
        error: Optional[str] = None,
        file_hash: Optional[str] = None,
        model_used: Optional[str] = None
    ) -> Dict:
        """
        Add a new entry to the processing log.
        Returns the created log entry.
        """
        log_data = self.load_log()
        
        # Generate output file paths
        base_name = Path(filename).stem
        text_file = self.transcriptions_dir / f"{base_name}.txt"
        json_file = self.json_dir / f"{base_name}.json"
        
        entry = {
            "filename": filename,
            "file_hash": file_hash,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "model_used": model_used or config.WHISPER_MODEL_SIZE,
            "language_detected": language,
            "text_file": str(text_file) if status == "success" else None,
            "json_file": str(json_file) if status == "success" else None,
            "error": error
        }
        
        log_data.append(entry)
        self.save_log(log_data)
        
        return entry
    
    def save_transcription(
        self,
        filename: str,
        transcription: str,
        metadata: Optional[Dict] = None
    ) -> Tuple[Path, Path]:
        """
        Save transcription in both text and JSON formats.
        Returns (text_file_path, json_file_path) tuple.
        """
        base_name = Path(filename).stem
        text_file = self.transcriptions_dir / f"{base_name}.txt"
        json_file = self.json_dir / f"{base_name}.json"
        
        # Save as text file
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(transcription)
        
        # Save as JSON with metadata
        json_data = {
            "filename": filename,
            "transcription": transcription,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return text_file, json_file
    
    def get_output_paths(self, filename: str) -> Tuple[Optional[Path], Optional[Path]]:
        """Get output file paths for a given filename."""
        base_name = Path(filename).stem
        text_file = self.transcriptions_dir / f"{base_name}.txt"
        json_file = self.json_dir / f"{base_name}.json"
        
        text_path = text_file if text_file.exists() else None
        json_path = json_file if json_file.exists() else None
        
        return text_path, json_path
    
    def cleanup_upload(self, file_path: Path):
        """Remove uploaded file after processing (optional cleanup)."""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors
