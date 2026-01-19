"""
PDF Exporter for Formatted Documents.

Exports FormattedDocument to PDF format using WeasyPrint (HTML to PDF).
Falls back to HTML export if WeasyPrint is not available.
"""
import logging
from pathlib import Path
from typing import Optional

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from core.models import FormattedDocument
from exports.base_exporter import BaseExporter
from exports.html_exporter import HTMLExporter
from core.errors import ExportError

logger = logging.getLogger(__name__)


class PDFExporter(BaseExporter):
    """
    Exports formatted documents to PDF format.
    
    Uses WeasyPrint to convert HTML to PDF, providing:
    - High-quality PDF output
    - Preserved Gurmukhi fonts
    - Print-ready formatting
    """
    
    def __init__(self):
        """Initialize PDF exporter."""
        super().__init__("pdf", ".pdf")
        
        # Use HTML exporter for conversion
        self.html_exporter = HTMLExporter()
        
        if not WEASYPRINT_AVAILABLE:
            logger.warning(
                "WeasyPrint not available. PDF export will require HTML conversion. "
                "Install with: pip install weasyprint"
            )
    
    def _export_impl(
        self,
        document: FormattedDocument,
        output_path: Path
    ) -> Path:
        """
        Export document to PDF file.
        
        Args:
            document: FormattedDocument to export
            output_path: Path where PDF file should be saved
        
        Returns:
            Path to exported PDF file
        """
        if not WEASYPRINT_AVAILABLE:
            raise ExportError(
                "pdf",
                "WeasyPrint is not installed. Install with: pip install weasyprint"
            )
        
        # Step 1: Generate HTML
        html_path = output_path.with_suffix('.html')
        try:
            self.html_exporter._export_impl(document, html_path)
            
            # Step 2: Convert HTML to PDF
            html_content = html_path.read_text(encoding='utf-8')
            HTML(string=html_content).write_pdf(output_path)
            
            logger.debug(f"Converted HTML to PDF: {output_path}")
            
        finally:
            # Clean up temporary HTML file
            if html_path.exists():
                html_path.unlink()
        
        logger.debug(f"Exported PDF document: {output_path} ({output_path.stat().st_size} bytes)")
        
        return output_path
