#!/usr/bin/env python3
"""
Build SGGS N-gram Language Model.

This script builds word-level and character-level N-gram language models
from the SGGS database for use in ASR rescoring.

Usage:
    python scripts/build_sggs_ngram.py [--output PATH] [--char-model] [--word-order N] [--char-order N]
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config
from data.sggs_language_model import SGGSLanguageModelBuilder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Build SGGS N-gram language model."""
    parser = argparse.ArgumentParser(
        description="Build SGGS N-gram language model for ASR rescoring"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path for model file (default: DATA_DIR/sggs_ngram.pkl)"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to SGGS database (default: config.SCRIPTURE_DB_PATH)"
    )
    parser.add_argument(
        "--word-order", "-w",
        type=int,
        default=3,
        help="N-gram order for word model (default: 3, trigram)"
    )
    parser.add_argument(
        "--char-order", "-c",
        type=int,
        default=4,
        help="N-gram order for character model (default: 4)"
    )
    parser.add_argument(
        "--build-char-model",
        action="store_true",
        default=False,
        help="Also build character-level model (slower, more memory)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine paths
    db_path = args.db_path or getattr(config, 'SCRIPTURE_DB_PATH', None)
    output_path = args.output or getattr(config, 'SGGS_NGRAM_MODEL_PATH', config.DATA_DIR / "sggs_ngram.pkl")
    
    if db_path is None or not Path(db_path).exists():
        logger.error(f"Database not found at {db_path}")
        logger.info("Please ensure SCRIPTURE_DB_PATH is set in config.py")
        return 1
    
    logger.info("="*60)
    logger.info("Building SGGS N-gram Language Model")
    logger.info("="*60)
    logger.info(f"Database: {db_path}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Word N-gram order: {args.word_order}")
    if args.build_char_model:
        logger.info(f"Char N-gram order: {args.char_order}")
    logger.info("")
    
    try:
        # Create builder
        builder = SGGSLanguageModelBuilder(db_path=db_path)
        
        # Build model
        model = builder.build(
            word_ngram_order=args.word_order,
            char_ngram_order=args.char_order,
            build_char_model=args.build_char_model
        )
        
        # Save model
        model.save(output_path)
        
        # Print summary
        logger.info("")
        logger.info("="*60)
        logger.info("Build Complete!")
        logger.info("="*60)
        logger.info(f"Lines processed: {model.line_count:,}")
        logger.info(f"Total words: {model.word_count:,}")
        
        if model.word_model:
            logger.info(f"Word vocabulary size: {len(model.word_model.vocabulary):,}")
            logger.info(f"Word N-gram count: {len(model.word_model.ngram_counts):,}")
        
        if model.char_model:
            logger.info(f"Char vocabulary size: {len(model.char_model.vocabulary):,}")
            logger.info(f"Char N-gram count: {len(model.char_model.ngram_counts):,}")
        
        logger.info(f"Model saved to: {output_path}")
        logger.info(f"File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        return 0
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        logger.exception("Traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())

