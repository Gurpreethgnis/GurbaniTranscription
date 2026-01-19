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


class ScriptConversionError(TranscriptionError):
    """Raised when script conversion fails."""
    
    def __init__(self, source_script: str, target_script: str, reason: str = ""):
        message = f"Script conversion failed: {source_script} → {target_script}"
        if reason:
            message += f". Reason: {reason}"
        message += "\nFix: Check input text for unsupported characters or invalid script"
        super().__init__(message)
        self.source_script = source_script
        self.target_script = target_script
        self.reason = reason


class AudioDenoiseError(TranscriptionError):
    """Raised when audio denoising fails."""
    
    def __init__(self, backend: str, reason: str = ""):
        message = f"Audio denoising failed (backend: {backend})"
        if reason:
            message += f": {reason}"
        message += f"\nFix: Check that {backend} is installed correctly (pip install {backend})"
        super().__init__(message)
        self.backend = backend
        self.reason = reason


class DocumentFormatError(TranscriptionError):
    """Raised when document formatting fails."""
    
    def __init__(self, reason: str = ""):
        message = "Document formatting failed"
        if reason:
            message += f": {reason}"
        message += "\nFix: Check that transcription result is valid and contains required segments"
        super().__init__(message)
        self.reason = reason


class ExportError(TranscriptionError):
    """Raised when document export fails."""
    
    def __init__(self, format: str, reason: str = ""):
        message = f"Document export failed (format: {format})"
        if reason:
            message += f": {reason}"
        message += f"\nFix: Check that {format} exporter is properly configured and dependencies are installed"
        super().__init__(message)
        self.format = format
        self.reason = reason