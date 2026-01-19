"""
Markdown Exporter for Formatted Documents.

Exports FormattedDocument to clean Markdown format with proper
section formatting and Gurbani quote styling.
"""
import logging
from pathlib import Path
from typing import List

from core.models import FormattedDocument, DocumentSection, QuoteContent
from exports.base_exporter import BaseExporter

logger = logging.getLogger(__name__)


class MarkdownExporter(BaseExporter):
    """
    Exports formatted documents to Markdown format.
    
    Produces clean, readable Markdown with:
    - Section headers
    - Styled Gurbani quotes
    - Metadata footnotes
    """
    
    def __init__(self):
        """Initialize Markdown exporter."""
        super().__init__("markdown", ".md")
    
    def _export_impl(
        self,
        document: FormattedDocument,
        output_path: Path
    ) -> Path:
        """
        Export document to Markdown file.
        
        Args:
            document: FormattedDocument to export
            output_path: Path where Markdown file should be saved
        
        Returns:
            Path to exported Markdown file
        """
        lines: List[str] = []
        
        # Title
        lines.append(f"# {document.title}\n")
        
        # Metadata header
        lines.append("---")
        lines.append(f"**Source:** {document.source_file}")
        lines.append(f"**Created:** {document.created_at}")
        if document.metadata:
            lines.append(f"**Total Sections:** {document.metadata.get('total_segments', len(document.sections))}")
        lines.append("---\n")
        
        # Sections
        for section in document.sections:
            section_md = self._format_section(section)
            lines.append(section_md)
            lines.append("")  # Blank line between sections
        
        # Write file
        content = "\n".join(lines)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.debug(f"Exported Markdown document: {output_path} ({len(content)} characters)")
        
        return output_path
    
    def _format_section(self, section: DocumentSection) -> str:
        """
        Format a document section as Markdown.
        
        Args:
            section: DocumentSection to format
        
        Returns:
            Markdown string
        """
        lines: List[str] = []
        
        # Section header based on type
        header = self._get_section_header(section.section_type)
        if header:
            lines.append(header)
        
        # Format content
        if isinstance(section.content, QuoteContent):
            lines.append(self._format_quote(section.content))
        else:
            # Regular text content
            text = str(section.content)
            # Preserve line breaks in text
            lines.append(text)
        
        # Add timestamp if available
        if section.start_time is not None:
            time_str = self._format_timestamp(section.start_time)
            lines.append(f"\n*[Time: {time_str}]*")
        
        return "\n".join(lines)
    
    def _get_section_header(self, section_type: str) -> str:
        """
        Get Markdown header for section type.
        
        Args:
            section_type: Section type identifier
        
        Returns:
            Markdown header string (empty if no header needed)
        """
        headers = {
            "opening_gurbani": "## Opening Gurbani",
            "fateh": "## Fateh",
            "topic": "## Topic",
            "quote": "## Gurbani Quote",
            "katha": ""  # No header for regular katha content
        }
        return headers.get(section_type, "")
    
    def _format_quote(self, quote: QuoteContent) -> str:
        """
        Format a Gurbani quote as Markdown.
        
        Args:
            quote: QuoteContent to format
        
        Returns:
            Markdown string
        """
        lines: List[str] = []
        
        # Gurmukhi text (centered, emphasized)
        lines.append(f"> **{quote.gurmukhi}**")
        lines.append("")
        
        # Roman transliteration (italicized)
        if quote.roman:
            lines.append(f"*{quote.roman}*")
            lines.append("")
        
        # English translation (if available)
        if quote.english_translation:
            lines.append(f"_{quote.english_translation}_")
            lines.append("")
        
        # Metadata
        metadata_parts = []
        if quote.source:
            metadata_parts.append(f"Source: {quote.source}")
        if quote.ang:
            metadata_parts.append(f"Ang: {quote.ang}")
        if quote.raag:
            metadata_parts.append(f"Raag: {quote.raag}")
        if quote.author:
            metadata_parts.append(f"Author: {quote.author}")
        
        if metadata_parts:
            lines.append(f"*({', '.join(metadata_parts)})*")
        
        # Context lines (if available)
        if quote.context_lines:
            lines.append("")
            lines.append("**Context:**")
            for context_line in quote.context_lines:
                lines.append(f"- {context_line}")
        
        return "\n".join(lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in readable format.
        
        Args:
            seconds: Time in seconds
        
        Returns:
            Formatted timestamp string (MM:SS)
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
