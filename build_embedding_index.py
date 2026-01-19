"""
Build Embedding Index Script.

Standalone CLI script to build FAISS embedding index from SGGS and Dasam Granth
databases for semantic quote matching.

Usage:
    python build_embedding_index.py [--sggs-only] [--dasam-only] [--max-lines N] 
                                    [--output PATH] [--model NAME] [--gpu] [--force]
"""
import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import config
from errors import DatabaseNotFoundError

# Setup logging with safe encoding for Windows console
import sys
if sys.platform == 'win32':
    # Use UTF-8 encoding for Windows console to handle Unicode
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass  # Fallback to default if reconfigure fails

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress warnings from embedding_index module during dependency checks
# (these warnings appear when the module is imported and dependencies are missing)
logging.getLogger('scripture.embedding_index').setLevel(logging.ERROR)
logging.getLogger('asr.asr_fusion').setLevel(logging.ERROR)  # Also suppress from asr_fusion


def check_dependencies() -> bool:
    """
    Check if required dependencies are installed.
    
    Returns:
        True if all dependencies are available, False otherwise
    """
    # Suppress warnings during dependency check
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        
        missing = []
        
        try:
            import numpy
            logger.debug("numpy: OK")
        except ImportError:
            missing.append("numpy>=1.24.0")
        
        try:
            from sentence_transformers import SentenceTransformer
            logger.debug("sentence-transformers: OK")
        except ImportError:
            missing.append("sentence-transformers>=2.2.0")
        
    try:
        import faiss
        logger.debug("faiss: OK")
    except ImportError:
        # Note: faiss-gpu is not available via pip on Windows
        # Use faiss-cpu for Windows, or install faiss-gpu via conda
        import platform
        if platform.system() == "Windows":
            missing.append("faiss-cpu>=1.7.4 (faiss-gpu not available on Windows via pip, use conda if needed)")
        else:
            missing.append("faiss-cpu>=1.7.4 (or faiss-gpu>=1.7.4 via conda)")
    
    if missing:
        logger.error("Missing required dependencies:")
        for dep in missing:
            logger.error(f"  - {dep}")
        logger.error("\nInstall with:")
        import platform
        if platform.system() == "Windows":
            # On Windows, faiss-gpu is not available via pip
            install_cmd = "pip install sentence-transformers>=2.2.0 faiss-cpu>=1.7.4"
            logger.error(f"  {install_cmd}")
            logger.error("\nNote: For GPU support on Windows, use conda:")
            logger.error("  conda install -c conda-forge faiss-gpu")
        else:
            logger.error(f"  pip install {' '.join(missing)}")
            logger.error("\nOr for GPU support:")
            logger.error("  conda install -c conda-forge faiss-gpu")
        return False
    
    return True


def check_gpu_faiss() -> bool:
    """
    Check if GPU-accelerated FAISS is available.
    
    Returns:
        True if faiss-gpu is available, False otherwise
    """
    try:
        import faiss
        # Try to create a GPU resource
        if hasattr(faiss, 'StandardGpuResources'):
            return True
    except Exception:
        pass
    return False


def validate_index(index_path: Path) -> bool:
    """
    Validate the built index by loading it and testing a search.
    
    Args:
        index_path: Path to the index file
        
    Returns:
        True if validation succeeds, False otherwise
    """
    logger.info("Validating index...")
    
    try:
        # Lazy import to avoid warnings if dependencies not installed
        from scripture.embedding_index import EmbeddingIndex
        
        # Check files exist
        if not index_path.exists():
            logger.error(f"Index file not found: {index_path}")
            return False
        
        metadata_path = index_path.with_suffix('.pkl')
        if not metadata_path.exists():
            logger.error(f"Metadata file not found: {metadata_path}")
            return False
        
        # Try to load index
        logger.info("Loading index for validation...")
        embedding_index = EmbeddingIndex(index_path=index_path)
        
        if embedding_index.index is None:
            logger.error("Failed to load index")
            return False
        
        # Get index statistics
        num_vectors = embedding_index.index.ntotal
        dimension = embedding_index.index.d
        
        logger.info(f"Index statistics:")
        logger.info(f"  - Vectors: {num_vectors:,}")
        logger.info(f"  - Dimension: {dimension}")
        logger.info(f"  - Index file size: {index_path.stat().st_size / 1024 / 1024:.2f} MB")
        logger.info(f"  - Metadata file size: {metadata_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Test search with a sample query
        test_query = "ਸਤਿਨਾਮੁ ਵਾਹਿਗੁਰੂ"
        # Avoid Unicode encoding issues on Windows console
        try:
            logger.info(f"Testing search with query: {test_query}")
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Windows console encoding issue - log in ASCII
            logger.info("Testing search with sample Gurmukhi query")
        
        results = embedding_index.search(test_query, top_k=5)
        
        if not results:
            logger.warning("Search returned no results (this may be normal if query doesn't match)")
        else:
            logger.info(f"Search returned {len(results)} results")
            for i, (line_id, similarity) in enumerate(results[:3], 1):
                logger.info(f"  {i}. line_id={line_id}, similarity={similarity:.4f}")
        
        logger.info("Index validation successful!")
        return True
        
    except Exception as e:
        logger.error(f"Index validation failed: {e}", exc_info=True)
        return False


def build_index(
    sggs_only: bool = False,
    dasam_only: bool = False,
    max_lines: Optional[int] = None,
    output_path: Optional[Path] = None,
    model_name: Optional[str] = None,
    use_gpu: bool = False,
    force: bool = False
) -> bool:
    """
    Build the embedding index from scripture databases.
    
    Args:
        sggs_only: Build index only from SGGS database
        dasam_only: Build index only from Dasam Granth database
        max_lines: Maximum number of lines to index (None = all)
        output_path: Override output path (default: config.EMBEDDING_INDEX_PATH)
        model_name: Override embedding model (default: config.EMBEDDING_MODEL)
        use_gpu: Use GPU-accelerated FAISS if available
        force: Overwrite existing index
        
    Returns:
        True if build succeeded, False otherwise
    """
    # Determine output path
    if output_path is None:
        output_path = config.EMBEDDING_INDEX_PATH
    else:
        output_path = Path(output_path)
    
    # Check if index already exists
    if output_path.exists() and not force:
        logger.error(f"Index already exists at {output_path}")
        logger.error("Use --force to overwrite")
        return False
    
    # Determine model name
    if model_name is None:
        model_name = config.EMBEDDING_MODEL
    
    logger.info("=" * 60)
    logger.info("Building Embedding Index")
    logger.info("=" * 60)
    logger.info(f"Output path: {output_path}")
    logger.info(f"Model: {model_name}")
    logger.info(f"Max lines: {max_lines if max_lines else 'all'}")
    logger.info(f"GPU: {use_gpu}")
    
    # Lazy import database classes
    from scripture.sggs_db import SGGSDatabase
    from scripture.dasam_db import DasamDatabase
    
    # Initialize databases
    sggs_db = None
    dasam_db = None
    
    # Connect to SGGS database
    if not dasam_only:
        try:
            logger.info("Connecting to SGGS database...")
            sggs_db = SGGSDatabase()
            logger.info(f"SGGS database connected: {sggs_db.db_path}")
        except DatabaseNotFoundError as e:
            logger.warning(f"SGGS database not found: {e}")
            if sggs_only:
                logger.error("Cannot build SGGS-only index without SGGS database")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to SGGS database: {e}", exc_info=True)
            if sggs_only:
                return False
    
    # Connect to Dasam Granth database
    if not sggs_only:
        try:
            logger.info("Connecting to Dasam Granth database...")
            dasam_db = DasamDatabase()
            if dasam_db._connection:
                logger.info(f"Dasam Granth database connected: {dasam_db.db_path}")
            else:
                logger.warning("Dasam Granth database not available")
                if dasam_only:
                    logger.error("Cannot build Dasam-only index without Dasam database")
                    return False
        except Exception as e:
            logger.warning(f"Failed to connect to Dasam Granth database: {e}")
            if dasam_only:
                return False
    
    # Check that at least one database is available
    if sggs_db is None and (dasam_db is None or dasam_db._connection is None):
        logger.error("No databases available. Cannot build index.")
        return False
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize embedding index
    try:
        # Lazy import to avoid warnings if dependencies not installed
        from scripture.embedding_index import EmbeddingIndex
        
        logger.info("Initializing embedding index...")
        embedding_index = EmbeddingIndex(
            model_name=model_name,
            index_path=output_path
        )
        
        # Note: GPU support would need to be implemented in EmbeddingIndex class
        # For now, we just log the preference
        if use_gpu:
            if check_gpu_faiss():
                logger.info("GPU-accelerated FAISS available")
            else:
                logger.warning("GPU FAISS requested but not available. Using CPU.")
        
        # Build index
        logger.info("Building index from databases...")
        embedding_index.build_index(
            sggs_db=sggs_db,
            dasam_db=dasam_db,
            max_lines=max_lines
        )
        
        if embedding_index.index is None:
            logger.error("Index build failed - no index created")
            return False
        
        logger.info("Index build completed successfully!")
        
        # Validate index
        if not validate_index(output_path):
            logger.warning("Index validation failed, but index was saved")
            return False
        
        return True
        
    except MemoryError:
        logger.error("Out of memory during index build")
        logger.error("Try using --max-lines to limit the number of lines indexed")
        return False
    except Exception as e:
        logger.error(f"Failed to build index: {e}", exc_info=True)
        return False


def main():
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description="Build FAISS embedding index from scripture databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build full index (SGGS + Dasam)
  python build_embedding_index.py

  # Build only SGGS index
  python build_embedding_index.py --sggs-only

  # Build with line limit (for testing)
  python build_embedding_index.py --max-lines 1000

  # Use GPU-accelerated FAISS
  python build_embedding_index.py --gpu

  # Override output path
  python build_embedding_index.py --output data/custom_index.faiss
        """
    )
    
    parser.add_argument(
        '--sggs-only',
        action='store_true',
        help='Build index only from SGGS database'
    )
    
    parser.add_argument(
        '--dasam-only',
        action='store_true',
        help='Build index only from Dasam Granth database'
    )
    
    parser.add_argument(
        '--max-lines',
        type=int,
        default=None,
        help='Maximum number of lines to index (for testing)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help=f'Output path for index (default: {config.EMBEDDING_INDEX_PATH})'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help=f'Embedding model name (default: {config.EMBEDDING_MODEL})'
    )
    
    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Use GPU-accelerated FAISS if available'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing index'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.sggs_only and args.dasam_only:
        logger.error("Cannot specify both --sggs-only and --dasam-only")
        sys.exit(1)
    
    # Check dependencies (suppress warnings during check)
    logger.info("Checking dependencies...")
    if not check_dependencies():
        logger.error("Missing required dependencies. Please install them first.")
        sys.exit(1)
    
    logger.info("All dependencies available")
    
    # Build index
    output_path = Path(args.output) if args.output else None
    
    success = build_index(
        sggs_only=args.sggs_only,
        dasam_only=args.dasam_only,
        max_lines=args.max_lines,
        output_path=output_path,
        model_name=args.model,
        use_gpu=args.gpu,
        force=args.force
    )
    
    if success:
        logger.info("=" * 60)
        logger.info("Build completed successfully!")
        logger.info("=" * 60)
        logger.info("To enable semantic search, set USE_EMBEDDING_SEARCH=true in your environment")
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("Build failed!")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
