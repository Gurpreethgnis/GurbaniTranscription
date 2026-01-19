"""
Base Exporter Implementation.

Provides base class for document exporters with common functionality.
"""
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from core.models import FormattedDocument, DocumentSection, QuoteContent
from core.errors import ExportError

logger = logging.getLogger(__name__)


class BaseExporter(ABC):
    """
    Base class for document exporters.
    
    Provides common functionality for all exporters:
    - File path validation
    - Directory creation
    - Error handling
    """
    
    def __init__(self, format_name: str, file_extension: str):
        """
        Initialize base exporter.
        
        Args:
            format_name: Format identifier (e.g., "pdf", "docx")
            file_extension: File extension (e.g., ".pdf", ".docx")
        """
        self.format_name = format_name
        self.file_extension = file_extension
    
    def export(
        self,
        document: FormattedDocument,
        output_path: Path
    ) -> Path:
        """
        Export document to file.
        
        Args:
            document: FormattedDocument to export
            output_path: Path where file should be saved
        
        Returns:
            Path to exported file
        
        Raises:
            ExportError: If export fails
        """
        # Ensure output path has correct extension
        if not output_path.suffix == self.file_extension:
            output_path = output_path.with_suffix(self.file_extension)
        
        # Create parent directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"Exporting document '{document.title}' to {self.format_name} format: {output_path}"
        )
        
        try:
            # Delegate to format-specific implementation
            result_path = self._export_impl(document, output_path)
            
            logger.info(f"Successfully exported {self.format_name} document: {result_path}")
            return result_path
            
        except Exception as e:
            error_msg = f"Failed to export {self.format_name} document: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExportError(self.format_name, error_msg) from e
    
    @abstractmethod
    def _export_impl(
        self,
        document: FormattedDocument,
        output_path: Path
    ) -> Path:
        """
        Format-specific export implementation.
        
        Args:
            document: FormattedDocument to export
            output_path: Path where file should be saved
        
        Returns:
            Path to exported file
        """
        pass
    
    def _get_section_text(self, section: DocumentSection) -> str:
        """
        Extract text content from a section.
        
        Args:
            section: DocumentSection
        
        Returns:
            Text content as string
        """
        if isinstance(section.content, QuoteContent):
            # For quotes, return Gurmukhi text
            return section.content.gurmukhi
        elif isinstance(section.content, str):
            return section.content
        else:
            return str(section.content)
    
    def _get_section_roman(self, section: DocumentSection) -> Optional[str]:
        """
        Extract Roman transliteration from a section (if available).
        
        Args:
            section: DocumentSection
        
        Returns:
            Roman text or None
        """
        if isinstance(section.content, QuoteContent):
            return section.content.roman
        # For text sections, Roman might be in segment metadata
        # but we don't have access here - return None
        return None
