"""
Custom exceptions for the transcription pipeline.

All exceptions must be explicit and provide clear error messages
explaining how to fix the issue.
"""


class TranscriptionError(Exception):
    """Base exception for all transcription errors."""
    pass


class AudioDecodeError(TranscriptionError):
    """Raised when audio file cannot be decoded."""
    
    def __init__(self, file_path: str, reason: str = ""):
        message = f"Failed to decode audio file: {file_path}"
        if reason:
            message += f" Reason: {reason}"
        message += "\nFix: Ensure the file is a valid audio format (mp3, wav, m4a, etc.)"
        super().__init__(message)
        self.file_path = file_path
        self.reason = reason


class ASREngineError(TranscriptionError):
    """Raised when an ASR engine fails."""
    
    def __init__(self, engine: str, reason: str = ""):
        message = f"ASR engine '{engine}' failed"
        if reason:
            message += f": {reason}"
        message += f"\nFix: Check that the {engine} model is loaded correctly"
        super().__init__(message)
        self.engine = engine
        self.reason = reason


class DatabaseNotFoundError(TranscriptionError):
    """Raised when a required database is not found."""
    
    def __init__(self, db_path: str, db_type: str = "scripture"):
        message = f"{db_type.capitalize()} database not found: {db_path}"
        message += f"\nFix: Download and place the {db_type} database at {db_path}"
        super().__init__(message)
        self.db_path = db_path
        self.db_type = db_type


class QuoteMatchError(TranscriptionError):
    """Raised when quote matching fails."""
    
    def __init__(self, reason: str = ""):
        message = "Quote matching failed"
        if reason:
            message += f": {reason}"
        message += "\nFix: Check quote candidate detection and matching logic"
        super().__init__(message)
        self.reason = reason


class FusionError(TranscriptionError):
    """Raised when ASR fusion fails."""
    
    def __init__(self, reason: str = ""):
        message = "ASR fusion failed"
        if reason:
            message += f": {reason}"
        message += "\nFix: Check that multiple ASR engines produced valid results"
        super().__init__(message)
        self.reason = reason


class VADError(TranscriptionError):
    """Raised when VAD (Voice Activity Detection) fails."""
    
    def __init__(self, reason: str = ""):
        message = "VAD chunking failed"
        if reason:
            message += f": {reason}"
        message += "\nFix: Check audio file format and VAD service configuration"
        super().__init__(message)
        self.reason = reason
