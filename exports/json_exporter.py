"""
JSON Exporter for Formatted Documents.

Exports FormattedDocument to structured JSON format suitable for
API consumption and pipeline ingestion.
"""
import json
import logging
from pathlib import Path

from core.models import FormattedDocument
from exports.base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class JSONExporter(BaseExporter):
    """
    Exports formatted documents to JSON format.
    
    Produces structured JSON with full metadata, suitable for:
    - API responses
    - Pipeline ingestion
    - Data analysis
    """
    
    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        """
        Initialize JSON exporter.
        
        Args:
            indent: JSON indentation level (default: 2)
            ensure_ascii: If False, allow Unicode characters (default: False)
        """
        super().__init__("json", ".json")
        self.indent = indent
        self.ensure_ascii = ensure_ascii
    
    def _export_impl(
        self,
        document: FormattedDocument,
        output_path: Path
    ) -> Path:
        """
        Export document to JSON file.
        
        Args:
            document: FormattedDocument to export
            output_path: Path where JSON file should be saved
        
        Returns:
            Path to exported JSON file
        """
        # Convert document to dictionary
        doc_dict = document.to_dict()
        
        # Write JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(
                doc_dict,
                f,
                indent=self.indent,
                ensure_ascii=self.ensure_ascii
            )
        
        logger.debug(f"Exported JSON document: {output_path} ({output_path.stat().st_size} bytes)")
        
        return output_path
