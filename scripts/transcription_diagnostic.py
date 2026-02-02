"""
Transcription Pipeline Diagnostic Script.

Runs an audio file through each pipeline stage separately and outputs
intermediate results to help identify where garbled output originates.

Usage:
    python scripts/transcription_diagnostic.py path/to/audio.mp3 [--output-dir ./diagnostics]
"""
import sys
import json
import tempfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import argparse

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


def run_diagnostic(
    audio_path: Path,
    output_dir: Optional[Path] = None,
    enable_denoising: bool = True,
    denoise_strength: str = "medium"
) -> Dict[str, Any]:
    """
    Run full pipeline diagnostic on an audio file.
    
    Args:
        audio_path: Path to input audio file
        output_dir: Directory to save diagnostic outputs (default: temp dir)
        enable_denoising: Whether to test with denoising
        denoise_strength: Denoising strength level
        
    Returns:
        Dictionary with diagnostic results from each stage
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # Create output directory
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="transcription_diagnostic_"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting diagnostic for: {audio_path}")
    logger.info(f"Output directory: {output_dir}")
    
    results = {
        "audio_file": str(audio_path),
        "output_dir": str(output_dir),
        "timestamp": datetime.now().isoformat(),
        "stages": {}
    }
    
    # Stage 0: Audio Info
    logger.info("=" * 60)
    logger.info("STAGE 0: Audio File Info")
    logger.info("=" * 60)
    
    try:
        from audio.audio_utils import get_audio_duration
        import soundfile as sf
        
        duration = get_audio_duration(audio_path)
        
        # Try to get more info with soundfile
        try:
            info = sf.info(str(audio_path))
            audio_info = {
                "duration_seconds": duration,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format,
                "subtype": info.subtype
            }
        except Exception:
            audio_info = {
                "duration_seconds": duration
            }
        
        results["stages"]["audio_info"] = audio_info
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info(f"  Info: {audio_info}")
        
    except Exception as e:
        logger.error(f"  Failed to get audio info: {e}")
        results["stages"]["audio_info"] = {"error": str(e)}
    
    # Stage 1: Denoising (optional)
    working_audio = audio_path
    
    if enable_denoising:
        logger.info("=" * 60)
        logger.info("STAGE 1: Denoising")
        logger.info("=" * 60)
        
        try:
            from audio.denoiser import AudioDenoiser
            
            denoiser = AudioDenoiser(
                backend="noisereduce",
                strength=denoise_strength
            )
            
            # Estimate noise level
            noise_level = denoiser.estimate_noise_level(audio_path)
            logger.info(f"  Estimated noise level: {noise_level:.2%}")
            
            # Denoise
            denoised_path = output_dir / "stage1_denoised.wav"
            working_audio = denoiser.denoise_file(audio_path, denoised_path)
            
            results["stages"]["denoising"] = {
                "noise_level": noise_level,
                "strength": denoise_strength,
                "output_file": str(denoised_path)
            }
            logger.info(f"  Denoised audio saved to: {denoised_path}")
            
        except Exception as e:
            logger.error(f"  Denoising failed: {e}")
            results["stages"]["denoising"] = {"error": str(e)}
            working_audio = audio_path
    else:
        logger.info("STAGE 1: Denoising SKIPPED")
        results["stages"]["denoising"] = {"skipped": True}
    
    # Stage 2: VAD Chunking
    logger.info("=" * 60)
    logger.info("STAGE 2: VAD Chunking")
    logger.info("=" * 60)
    
    chunks = []
    try:
        from services.vad_service import VADService
        import config
        
        vad = VADService(
            aggressiveness=getattr(config, 'VAD_AGGRESSIVENESS', 2),
            min_chunk_duration=getattr(config, 'VAD_MIN_CHUNK_DURATION', 1.0),
            max_chunk_duration=getattr(config, 'VAD_MAX_CHUNK_DURATION', 30.0),
            overlap_seconds=getattr(config, 'VAD_OVERLAP_SECONDS', 0.5)
        )
        
        chunks = vad.chunk_audio(working_audio)
        
        chunk_info = []
        for i, chunk in enumerate(chunks):
            info = {
                "index": i,
                "start": chunk.start_time,
                "end": chunk.end_time,
                "duration": chunk.duration
            }
            chunk_info.append(info)
            logger.info(f"  Chunk {i}: {chunk.start_time:.2f}s - {chunk.end_time:.2f}s ({chunk.duration:.2f}s)")
        
        results["stages"]["vad_chunking"] = {
            "num_chunks": len(chunks),
            "chunks": chunk_info
        }
        
    except Exception as e:
        logger.error(f"  VAD chunking failed: {e}")
        results["stages"]["vad_chunking"] = {"error": str(e)}
    
    # Stage 3: Language Identification
    logger.info("=" * 60)
    logger.info("STAGE 3: Language Identification")
    logger.info("=" * 60)
    
    langid_results = []
    try:
        from services.langid_service import LangIDService
        from asr.asr_whisper import ASRWhisper
        
        # Create minimal ASR for quick detection
        asr = ASRWhisper()
        langid = LangIDService(quick_asr_service=asr)
        
        for i, chunk in enumerate(chunks):
            try:
                route = langid.identify_segment(chunk)
                language = langid.get_language_code(route)
                
                info = {
                    "chunk_index": i,
                    "route": route,
                    "language": language
                }
                langid_results.append(info)
                logger.info(f"  Chunk {i}: route={route}, language={language}")
                
            except Exception as e:
                logger.warning(f"  Chunk {i}: LangID failed - {e}")
                langid_results.append({"chunk_index": i, "error": str(e)})
        
        results["stages"]["langid"] = {
            "results": langid_results
        }
        
    except Exception as e:
        logger.error(f"  Language identification failed: {e}")
        results["stages"]["langid"] = {"error": str(e)}
    
    # Stage 4: Raw ASR Transcription
    logger.info("=" * 60)
    logger.info("STAGE 4: Raw ASR Transcription (per chunk)")
    logger.info("=" * 60)
    
    asr_results = []
    try:
        from asr.asr_whisper import ASRWhisper
        
        asr = ASRWhisper()
        
        for i, chunk in enumerate(chunks):
            try:
                # Get language hint from langid if available
                lang_hint = None
                if i < len(langid_results) and "language" in langid_results[i]:
                    lang_hint = langid_results[i]["language"]
                
                # Transcribe chunk
                asr_result = asr.transcribe_chunk(
                    chunk.audio_path,
                    language=lang_hint,
                    chunk_start=chunk.start_time
                )
                
                info = {
                    "chunk_index": i,
                    "text": asr_result.text,
                    "language": asr_result.language,
                    "confidence": asr_result.confidence,
                    "engine": asr_result.engine
                }
                asr_results.append(info)
                
                # Show result (truncate long text)
                text_preview = asr_result.text[:80] + "..." if len(asr_result.text) > 80 else asr_result.text
                logger.info(f"  Chunk {i} ({asr_result.language}, conf={asr_result.confidence:.2f}):")
                logger.info(f"    {text_preview}")
                
            except Exception as e:
                logger.warning(f"  Chunk {i}: ASR failed - {e}")
                asr_results.append({"chunk_index": i, "error": str(e)})
        
        results["stages"]["raw_asr"] = {
            "results": asr_results,
            "full_text": " ".join(r.get("text", "") for r in asr_results if "text" in r)
        }
        
    except Exception as e:
        logger.error(f"  Raw ASR transcription failed: {e}")
        results["stages"]["raw_asr"] = {"error": str(e)}
    
    # Stage 5: Full Orchestrator Pipeline
    logger.info("=" * 60)
    logger.info("STAGE 5: Full Orchestrator Pipeline")
    logger.info("=" * 60)
    
    try:
        from core.orchestrator import Orchestrator
        
        orch = Orchestrator()
        
        processing_options = {
            "denoiseEnabled": enable_denoising,
            "denoiseStrength": denoise_strength,
        }
        
        result = orch.transcribe_file(
            audio_path,
            mode="batch",
            processing_options=processing_options
        )
        
        # Extract results
        gurmukhi_text = result.transcription.get("gurmukhi", "")
        roman_text = result.transcription.get("roman", "")
        
        segments_info = []
        for i, seg in enumerate(result.segments):
            info = {
                "index": i,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "confidence": seg.confidence,
                "language": seg.language,
                "route": seg.route,
                "type": seg.type,
                "needs_review": seg.needs_review
            }
            segments_info.append(info)
            
            text_preview = seg.text[:60] + "..." if len(seg.text) > 60 else seg.text
            conf_str = f"conf={seg.confidence:.2f}"
            logger.info(f"  Segment {i} ({seg.language}, {conf_str}, needs_review={seg.needs_review}):")
            logger.info(f"    {text_preview}")
        
        results["stages"]["orchestrator"] = {
            "gurmukhi_text": gurmukhi_text,
            "roman_text": roman_text,
            "segments": segments_info,
            "metrics": result.metrics
        }
        
        logger.info(f"\n  FINAL GURMUKHI TEXT:")
        logger.info(f"    {gurmukhi_text[:200]}..." if len(gurmukhi_text) > 200 else f"    {gurmukhi_text}")
        
    except Exception as e:
        logger.error(f"  Orchestrator pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        results["stages"]["orchestrator"] = {"error": str(e)}
    
    # Save diagnostic results
    logger.info("=" * 60)
    logger.info("Saving diagnostic results...")
    logger.info("=" * 60)
    
    output_file = output_dir / "diagnostic_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to: {output_file}")
    
    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("DIAGNOSTIC SUMMARY")
    logger.info("=" * 60)
    
    for stage_name, stage_data in results["stages"].items():
        if "error" in stage_data:
            logger.info(f"  {stage_name}: ❌ FAILED - {stage_data['error'][:50]}...")
        elif stage_data.get("skipped"):
            logger.info(f"  {stage_name}: ⏭️ SKIPPED")
        else:
            logger.info(f"  {stage_name}: ✅ OK")
    
    return results


def compare_raw_vs_orchestrated(results: Dict[str, Any]) -> None:
    """Compare raw ASR output with full orchestrator output."""
    
    raw_text = results.get("stages", {}).get("raw_asr", {}).get("full_text", "")
    orch_text = results.get("stages", {}).get("orchestrator", {}).get("gurmukhi_text", "")
    
    print("\n" + "=" * 60)
    print("RAW ASR vs ORCHESTRATOR COMPARISON")
    print("=" * 60)
    
    print("\nRaw ASR output (before post-processing):")
    print("-" * 40)
    print(raw_text[:500] if raw_text else "(empty)")
    
    print("\nOrchestrator output (after full pipeline):")
    print("-" * 40)
    print(orch_text[:500] if orch_text else "(empty)")
    
    if raw_text and orch_text:
        # Check if they're significantly different
        if raw_text.strip() == orch_text.strip():
            print("\n✅ Raw and orchestrated outputs are identical")
        else:
            # Calculate rough similarity
            raw_words = set(raw_text.lower().split())
            orch_words = set(orch_text.lower().split())
            
            common = len(raw_words & orch_words)
            total = len(raw_words | orch_words)
            
            similarity = common / total if total > 0 else 0
            print(f"\n⚠️ Outputs differ - word-level similarity: {similarity:.1%}")
            
            if similarity < 0.5:
                print("   This suggests significant changes during post-processing")
                print("   Check quote replacement, domain correction, or script conversion")


def main():
    parser = argparse.ArgumentParser(
        description="Run transcription pipeline diagnostic on an audio file"
    )
    parser.add_argument(
        "audio_path",
        type=Path,
        help="Path to audio file to diagnose"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=None,
        help="Directory to save diagnostic outputs"
    )
    parser.add_argument(
        "--no-denoise",
        action="store_true",
        help="Skip denoising stage"
    )
    parser.add_argument(
        "--denoise-strength",
        choices=["light", "medium", "aggressive"],
        default="medium",
        help="Denoising strength level"
    )
    
    args = parser.parse_args()
    
    # Run diagnostic
    results = run_diagnostic(
        audio_path=args.audio_path,
        output_dir=args.output_dir,
        enable_denoising=not args.no_denoise,
        denoise_strength=args.denoise_strength
    )
    
    # Show comparison
    compare_raw_vs_orchestrated(results)


if __name__ == "__main__":
    main()
