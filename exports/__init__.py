"""
Document Export Module.

Provides exporters for different document formats (PDF, DOCX, Markdown, HTML, JSON).
"""
from typing import Protocol, List
from pathlib import Path

from core.models import FormattedDocument


class Exporter(Protocol):
    """Protocol for document exporters."""
    
    def export(
        self,
        document: FormattedDocument,
        output_path: Path
    ) -> Path:
        """
        Export a formatted document to a file.
        
        Args:
            document: FormattedDocument to export
            output_path: Path where exported file should be saved
        
        Returns:
            Path to the exported file
        
        Raises:
            ExportError: If export fails
        """
        ...


class ExportManager:
    """
    Manages document exports in multiple formats.
    
    Provides a unified interface for exporting documents to different formats.
    """
    
    def __init__(self):
        """Initialize export manager."""
        self._exporters: dict[str, Exporter] = {}
    
    def register_exporter(self, format_name: str, exporter: Exporter) -> None:
        """
        Register an exporter for a format.
        
        Args:
            format_name: Format identifier (e.g., "pdf", "docx", "markdown")
            exporter: Exporter instance
        """
        self._exporters[format_name.lower()] = exporter
    
    def get_exporter(self, format_name: str) -> Exporter:
        """
        Get exporter for a format.
        
        Args:
            format_name: Format identifier
        
        Returns:
            Exporter instance
        
        Raises:
            ValueError: If format is not supported
        """
        format_lower = format_name.lower()
        if format_lower not in self._exporters:
            supported = ", ".join(self._exporters.keys())
            raise ValueError(
                f"Format '{format_name}' not supported. "
                f"Supported formats: {supported}"
            )
        return self._exporters[format_lower]
    
    def export(
        self,
        document: FormattedDocument,
        format_name: str,
        output_path: Path
    ) -> Path:
        """
        Export document in specified format.
        
        Args:
            document: FormattedDocument to export
            format_name: Format identifier
            output_path: Path where exported file should be saved
        
        Returns:
            Path to the exported file
        """
        exporter = self.get_exporter(format_name)
        return exporter.export(document, output_path)
    
    def get_supported_formats(self) -> List[str]:
        """
        Get list of supported export formats.
        
        Returns:
            List of format names
        """
        return list(self._exporters.keys())
