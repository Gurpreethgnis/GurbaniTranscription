#!/usr/bin/env python3
"""
CLI tool for Punjabi speech-to-text transcription.

Usage:
    python -m cli.transcribe audio.wav --model whisper --out json
    python -m cli.transcribe ./audio_folder/ --model indicconformer --out srt
    python -m cli.transcribe audio.mp3 --model wav2vec2 --out txt --language pa

Features:
    - Single file or directory input
    - Provider selection (whisper, indicconformer, wav2vec2, commercial)
    - Output formats (json, txt, srt)
    - Language hint
    - Timestamps toggle
    - Progress bar for batch processing
"""
import sys
import os
import argparse
import json
from pathlib import Path
from typing import Optional, List
from datetime import timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from core.orchestrator import Orchestrator
from asr.provider_registry import get_registry, ProviderType

# Try to import rich for better output
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def print_info(message: str):
    """Print info message."""
    if RICH_AVAILABLE:
        console.print(f"[blue]ℹ[/blue] {message}")
    else:
        print(f"INFO: {message}")


def print_success(message: str):
    """Print success message."""
    if RICH_AVAILABLE:
        console.print(f"[green]✓[/green] {message}")
    else:
        print(f"SUCCESS: {message}")


def print_error(message: str):
    """Print error message."""
    if RICH_AVAILABLE:
        console.print(f"[red]✗[/red] {message}")
    else:
        print(f"ERROR: {message}", file=sys.stderr)


def print_warning(message: str):
    """Print warning message."""
    if RICH_AVAILABLE:
        console.print(f"[yellow]⚠[/yellow] {message}")
    else:
        print(f"WARNING: {message}")


def format_time(seconds: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    td = timedelta(seconds=seconds)
    hours = int(td.total_seconds() // 3600)
    minutes = int((td.total_seconds() % 3600) // 60)
    secs = td.total_seconds() % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace(".", ",")


def generate_srt(segments: List[dict]) -> str:
    """
    Generate SRT subtitle format from segments.
    
    Args:
        segments: List of segment dicts with start, end, text
    
    Returns:
        SRT formatted string
    """
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start = format_time(seg.get("start", 0))
        end = format_time(seg.get("end", 0))
        text = seg.get("text", "").strip()
        
        srt_lines.append(f"{i}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(text)
        srt_lines.append("")  # Empty line between entries
    
    return "\n".join(srt_lines)


def transcribe_file(
    audio_path: Path,
    model: str,
    language: str,
    timestamps: bool,
    orchestrator: Orchestrator,
    domain_mode: str = "sggs",
    strict_gurmukhi: bool = True
) -> dict:
    """
    Transcribe a single audio file.
    
    Args:
        audio_path: Path to audio file
        model: ASR model/provider name
        language: Language code
        timestamps: Whether to include timestamps
        orchestrator: Orchestrator instance
        domain_mode: Domain mode for language prioritization
        strict_gurmukhi: Whether to enforce strict Gurmukhi output
    
    Returns:
        Dict with transcription result
    """
    print_info(f"Transcribing: {audio_path.name}")
    
    try:
        # Get the provider
        if model == "whisper":
            # Use the primary ASR service (Whisper)
            result = orchestrator.transcribe_file(
                audio_path,
                mode="batch",
                domain_mode=domain_mode,
                strict_gurmukhi=strict_gurmukhi
            )
        else:
            # Use specific provider from registry
            provider = orchestrator.get_provider(model)
            asr_result = provider.transcribe_file(audio_path, language=language)
            
            # Convert to TranscriptionResult format
            from core.models import ProcessedSegment, TranscriptionResult
            
            segments = [
                ProcessedSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    confidence=seg.confidence,
                    language=seg.language or language,
                    route="direct",
                    type="speech"
                )
                for seg in asr_result.segments
            ]
            
            result = TranscriptionResult(
                filename=audio_path.name,
                segments=segments,
                transcription={
                    "gurmukhi": asr_result.text,
                    "roman": ""
                },
                metrics={
                    "provider": model,
                    "confidence": asr_result.confidence
                }
            )
        
        # Build output dict
        output = {
            "filename": audio_path.name,
            "text": result.transcription.get("gurmukhi", "") or " ".join(s.text for s in result.segments),
            "language": language,
            "provider": model,
            "confidence": result.metrics.get("average_confidence") or result.metrics.get("confidence", 0)
        }
        
        if timestamps:
            output["segments"] = [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "confidence": seg.confidence
                }
                for seg in result.segments
            ]
        
        return output
        
    except Exception as e:
        print_error(f"Failed to transcribe {audio_path.name}: {e}")
        return {
            "filename": audio_path.name,
            "error": str(e)
        }


def write_output(result: dict, output_path: Path, format: str):
    """
    Write transcription result to file.
    
    Args:
        result: Transcription result dict
        output_path: Output file path
        format: Output format (json, txt, srt)
    """
    if "error" in result:
        print_warning(f"Skipping output for {result['filename']} due to error")
        return
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    elif format == "txt":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.get("text", ""))
    
    elif format == "srt":
        segments = result.get("segments", [])
        if not segments:
            # Create single segment from full text
            segments = [{
                "start": 0,
                "end": 0,
                "text": result.get("text", "")
            }]
        
        srt_content = generate_srt(segments)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
    
    print_success(f"Output written to: {output_path}")


def list_providers():
    """List available ASR providers."""
    registry = get_registry()
    providers = registry.get_capabilities()
    
    if RICH_AVAILABLE:
        table = Table(title="Available ASR Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Available", style="green")
        table.add_column("Languages", style="yellow")
        table.add_column("Timestamps", style="blue")
        
        for provider_id, caps in providers.items():
            available = "✓" if caps.get("is_available") else "✗"
            available_style = "green" if caps.get("is_available") else "red"
            languages = ", ".join(caps.get("supported_languages", [])[:4])
            if len(caps.get("supported_languages", [])) > 4:
                languages += "..."
            timestamps = "✓" if caps.get("supports_timestamps") else "✗"
            
            table.add_row(
                provider_id,
                caps.get("name", ""),
                f"[{available_style}]{available}[/{available_style}]",
                languages,
                timestamps
            )
        
        console.print(table)
    else:
        print("\nAvailable ASR Providers:")
        print("-" * 60)
        for provider_id, caps in providers.items():
            available = "Available" if caps.get("is_available") else "Not Available"
            print(f"  {provider_id}: {caps.get('name', '')} ({available})")
            print(f"    Languages: {', '.join(caps.get('supported_languages', []))}")
            print(f"    Timestamps: {'Yes' if caps.get('supports_timestamps') else 'No'}")
        print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Punjabi Speech-to-Text Transcription CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s audio.wav                        # Transcribe with defaults (whisper, json)
  %(prog)s audio.mp3 --model indicconformer # Use IndicConformer model
  %(prog)s folder/ --out srt                # Batch transcribe to SRT
  %(prog)s audio.wav --model wav2vec2 --language pa --out txt
  %(prog)s --list-providers                 # List available providers
        """
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="Audio file or directory to transcribe"
    )
    
    parser.add_argument(
        "--model", "-m",
        choices=["whisper", "indicconformer", "wav2vec2", "commercial"],
        default="whisper",
        help="ASR model/provider to use (default: whisper)"
    )
    
    parser.add_argument(
        "--out", "-o",
        choices=["json", "txt", "srt"],
        default="json",
        help="Output format (default: json)"
    )
    
    parser.add_argument(
        "--language", "-l",
        default="pa",
        help="Language code hint (default: pa for Punjabi)"
    )
    
    parser.add_argument(
        "--timestamps/--no-timestamps",
        default=True,
        dest="timestamps",
        action=argparse.BooleanOptionalAction,
        help="Include timestamps in output (default: True)"
    )
    
    parser.add_argument(
        "--output-dir", "-d",
        type=Path,
        default=None,
        help="Output directory (default: same as input)"
    )
    
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available ASR providers and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Domain language prioritization options
    parser.add_argument(
        "--mode",
        choices=["sggs", "dasam", "generic"],
        default="sggs",
        help="Domain mode for language prioritization (default: sggs)"
    )
    
    parser.add_argument(
        "--strict-gurmukhi/--no-strict-gurmukhi",
        default=True,
        dest="strict_gurmukhi",
        action=argparse.BooleanOptionalAction,
        help="Enforce strict Gurmukhi-only output (default: True)"
    )
    
    # SGGS Enhancement options
    parser.add_argument(
        "--gurbani-prompting/--no-gurbani-prompting",
        default=True,
        dest="gurbani_prompting",
        action=argparse.BooleanOptionalAction,
        help="Enable Gurbani vocabulary prompting for Whisper (default: True)"
    )
    
    parser.add_argument(
        "--ngram-rescoring/--no-ngram-rescoring",
        default=True,
        dest="ngram_rescoring",
        action=argparse.BooleanOptionalAction,
        help="Enable N-gram LM rescoring with SGGS corpus (default: True)"
    )
    
    parser.add_argument(
        "--quote-alignment/--no-quote-alignment",
        default=True,
        dest="quote_alignment",
        action=argparse.BooleanOptionalAction,
        help="Enable automatic alignment/snapping to canonical SGGS text (default: True)"
    )
    
    args = parser.parse_args()
    
    # Handle list providers
    if args.list_providers:
        list_providers()
        return 0
    
    # Require input if not listing providers
    if not args.input:
        parser.error("Input file or directory is required")
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print_error(f"Input not found: {input_path}")
        return 1
    
    # Determine files to process
    if input_path.is_file():
        audio_files = [input_path]
    else:
        # Directory: find audio files
        audio_files = []
        for ext in config.SUPPORTED_FORMATS:
            audio_files.extend(input_path.glob(f"*{ext}"))
        audio_files = sorted(audio_files)
        
        if not audio_files:
            print_error(f"No audio files found in: {input_path}")
            return 1
        
        print_info(f"Found {len(audio_files)} audio file(s)")
    
    # Initialize orchestrator
    print_info(f"Initializing {args.model} provider...")
    print_info(f"Domain mode: {args.mode}, strict Gurmukhi: {args.strict_gurmukhi}")
    print_info(f"SGGS enhancements: prompting={args.gurbani_prompting}, ngram={args.ngram_rescoring}, alignment={args.quote_alignment}")
    
    try:
        # Set SGGS enhancement config before orchestrator init
        config.ENABLE_GURBANI_PROMPTING = args.gurbani_prompting
        config.ENABLE_NGRAM_RESCORING = args.ngram_rescoring
        config.ENABLE_QUOTE_ALIGNMENT = args.quote_alignment
        
        orchestrator = Orchestrator(primary_provider=args.model)
        orchestrator.set_domain_mode(args.mode, args.strict_gurmukhi)
    except Exception as e:
        print_error(f"Failed to initialize orchestrator: {e}")
        return 1
    
    # Determine output directory
    output_dir = args.output_dir or (input_path.parent if input_path.is_file() else input_path)
    
    # Process files
    results = []
    
    if RICH_AVAILABLE and len(audio_files) > 1:
        # Use progress bar for batch processing
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Transcribing...", total=len(audio_files))
            
            for audio_file in audio_files:
                progress.update(task, description=f"Processing {audio_file.name}")
                result = transcribe_file(
                    audio_file,
                    args.model,
                    args.language,
                    args.timestamps,
                    orchestrator,
                    domain_mode=args.mode,
                    strict_gurmukhi=args.strict_gurmukhi
                )
                results.append(result)
                
                # Write output
                output_name = audio_file.stem + f".{args.out}"
                output_path = output_dir / output_name
                write_output(result, output_path, args.out)
                
                progress.advance(task)
    else:
        # Simple processing
        for audio_file in audio_files:
            result = transcribe_file(
                audio_file,
                args.model,
                args.language,
                args.timestamps,
                orchestrator,
                domain_mode=args.mode,
                strict_gurmukhi=args.strict_gurmukhi
            )
            results.append(result)
            
            # Write output
            output_name = audio_file.stem + f".{args.out}"
            output_path = output_dir / output_name
            write_output(result, output_path, args.out)
    
    # Summary
    successful = sum(1 for r in results if "error" not in r)
    failed = len(results) - successful
    
    print()
    if failed == 0:
        print_success(f"Completed: {successful} file(s) transcribed successfully")
    else:
        print_warning(f"Completed: {successful} successful, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

