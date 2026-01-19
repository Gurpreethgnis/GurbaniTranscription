"""
Document Formatter.

Transforms TranscriptionResult into a structured FormattedDocument
with classified sections and enriched quote content.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.models import (
    TranscriptionResult,
    ProcessedSegment,
    FormattedDocument,
    DocumentSection,
    QuoteContent,
    QuoteMatch,
    ScriptureSource
)
from post.section_classifier import SectionClassifier, ClassifiedSection
from scripture.sggs_db import SGGSDatabase
from scripture.dasam_db import DasamDatabase
from core.errors import DocumentFormatError
import config

logger = logging.getLogger(__name__)


class DocumentFormatter:
    """
    Formats transcription results into structured documents.
    
    Uses SectionClassifier to identify sections and enriches quote content
    with metadata and context from scripture databases.
    """
    
    def __init__(
        self,
        classifier: Optional[SectionClassifier] = None,
        sggs_db: Optional[SGGSDatabase] = None,
        dasam_db: Optional[DasamDatabase] = None
    ):
        """
        Initialize document formatter.
        
        Args:
            classifier: SectionClassifier instance (created if None)
            sggs_db: SGGS database instance (created if None, if DB exists)
            dasam_db: Dasam Granth database instance (created if None, if DB exists)
        """
        self.classifier = classifier or SectionClassifier()
        
        # Initialize scripture databases if available
        self.sggs_db = None
        self.dasam_db = None
        
        try:
            if sggs_db is not None:
                self.sggs_db = sggs_db
            elif config.SCRIPTURE_DB_PATH.exists():
                self.sggs_db = SGGSDatabase()
                logger.info("SGGS database initialized for document formatting")
        except Exception as e:
            logger.warning(f"Could not initialize SGGS database: {e}")
        
        try:
            if dasam_db is not None:
                self.dasam_db = dasam_db
            elif config.DASAM_DB_PATH.exists():
                self.dasam_db = DasamDatabase()
                logger.info("Dasam Granth database initialized for document formatting")
        except Exception as e:
            logger.warning(f"Could not initialize Dasam Granth database: {e}")
        
        logger.info("DocumentFormatter initialized")
    
    def format_document(
        self,
        result: TranscriptionResult
    ) -> FormattedDocument:
        """
        Format a transcription result into a structured document.
        
        Args:
            result: TranscriptionResult to format
        
        Returns:
            FormattedDocument with classified sections
        """
        if not result.segments:
            raise DocumentFormatError("TranscriptionResult has no segments")
        
        logger.info(f"Formatting document from {result.filename} ({len(result.segments)} segments)")
        
        # Step 1: Classify segments
        classified = self.classifier.classify_segments(result.segments)
        
        # Step 2: Build document sections
        document_sections = []
        
        for classified_section in classified:
            doc_section = self._build_document_section(classified_section)
            if doc_section:
                document_sections.append(doc_section)
        
        # Step 3: Extract metadata
        title = Path(result.filename).stem
        
        metadata = {
            **result.metrics,
            "total_sections": len(document_sections),
            "opening_gurbani_count": sum(
                1 for s in document_sections if s.section_type == "opening_gurbani"
            ),
            "quote_count": sum(
                1 for s in document_sections if s.section_type == "quote"
            ),
            "has_fateh": any(s.section_type == "fateh" for s in document_sections),
            "has_topic": any(s.section_type == "topic" for s in document_sections)
        }
        
        # Step 4: Create formatted document
        formatted_doc = FormattedDocument(
            title=title,
            source_file=result.filename,
            created_at=datetime.now().isoformat(),
            sections=document_sections,
            metadata=metadata
        )
        
        logger.info(
            f"Document formatted: {len(document_sections)} sections, "
            f"title='{title}'"
        )
        
        return formatted_doc
    
    def _build_document_section(
        self,
        classified: ClassifiedSection
    ) -> Optional[DocumentSection]:
        """
        Build a DocumentSection from a ClassifiedSection.
        
        Args:
            classified: ClassifiedSection to convert
        
        Returns:
            DocumentSection or None if conversion fails
        """
        segment = classified.segment
        
        # Handle quote sections (opening_gurbani or quote)
        if classified.section_type in ["opening_gurbani", "quote"]:
            if segment.quote_match is None:
                logger.warning(
                    f"Segment at {segment.start:.2f}s marked as quote but has no quote_match"
                )
                return None
            
            quote_content = self._build_quote_content(segment.quote_match)
            if quote_content:
                return DocumentSection(
                    section_type=classified.section_type,
                    content=quote_content,
                    start_time=segment.start,
                    end_time=segment.end,
                    confidence=classified.confidence
                )
            else:
                # Fallback: use text content
                return DocumentSection(
                    section_type=classified.section_type,
                    content=segment.text,
                    start_time=segment.start,
                    end_time=segment.end,
                    confidence=classified.confidence
                )
        
        # Handle text sections (fateh, topic, katha)
        content_text = segment.text
        if segment.roman and classified.section_type != "fateh":
            # For non-fateh sections, prefer Gurmukhi but include Roman if available
            # (Fateh is usually already in Roman/English)
            pass  # Use Gurmukhi text as primary
        
        return DocumentSection(
            section_type=classified.section_type,
            content=content_text,
            start_time=segment.start,
            end_time=segment.end,
            confidence=classified.confidence
        )
    
    def _build_quote_content(
        self,
        quote_match: QuoteMatch
    ) -> Optional[QuoteContent]:
        """
        Build QuoteContent from a QuoteMatch, enriching with context.
        
        Args:
            quote_match: QuoteMatch to convert
        
        Returns:
            QuoteContent or None if conversion fails
        """
        # Get context lines if database is available
        context_lines = []
        try:
            if quote_match.source == ScriptureSource.SGGS and self.sggs_db:
                context = self.sggs_db.get_context(quote_match.line_id, window=2)
                context_lines = [line.gurmukhi for line in context if line.gurmukhi != quote_match.canonical_text]
            elif quote_match.source == ScriptureSource.DasamGranth and self.dasam_db:
                # Dasam DB might have similar method
                context_lines = []
        except Exception as e:
            logger.debug(f"Could not get context for line {quote_match.line_id}: {e}")
        
        # Build QuoteContent
        quote_content = QuoteContent(
            gurmukhi=quote_match.canonical_text,
            roman=quote_match.canonical_roman or "",
            source=quote_match.source.value,
            ang=quote_match.ang,
            raag=quote_match.raag,
            author=quote_match.author,
            context_lines=context_lines[:4],  # Limit to 4 context lines
            line_id=quote_match.line_id,
            shabad_id=None  # Could be extracted from quote_match if available
        )
        
        # Try to get English translation if available
        # (This would require additional database fields or translation service)
        # For now, leave as None
        
        return quote_content
    
    def close(self):
        """Close database connections."""
        if self.sggs_db:
            try:
                self.sggs_db.close()
            except Exception:
                pass
        if self.dasam_db:
            try:
                self.dasam_db.close()
            except Exception:
                pass
