"""
Transcription Accuracy Testing.

Two audio sources supported:
1. TTS-generated audio (gTTS) - synthetic but convenient
2. Kaggle Punjabi Speech Recognition dataset - real speech, more realistic

This helps diagnose where garbled output might be coming from:
- Denoiser issues
- VAD chunking problems  
- ASR model issues

Kaggle Dataset Usage:
    pip install kagglehub
    import kagglehub
    path = kagglehub.dataset_download("warcoder/punjabi-speech-recognition")
"""
import sys
import tempfile
import csv
import os
from pathlib import Path
import unittest
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# Kaggle dataset path (set after download)
KAGGLE_DATASET_PATH: Optional[Path] = None

# Test phrases with known transcriptions
# Format: (input_text_for_tts, expected_output_gurmukhi, language_code)
TEST_PHRASES = [
    # Simple Punjabi phrases
    ("waheguru ji ka khalsa waheguru ji ki fateh", "ਵਾਹਿਗੁਰੂ ਜੀ ਕਾ ਖਾਲਸਾ ਵਾਹਿਗੁਰੂ ਜੀ ਕੀ ਫਤਿਹ", "pa"),
    ("sat sri akal", "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ", "pa"),
    ("ik onkar satnam", "ੴ ਸਤਿ ਨਾਮ", "pa"),
    
    # English phrases (for mixed content testing)
    ("This is a test of the transcription system", "This is a test of the transcription system", "en"),
    
    # Hindi (for Indic ASR testing)  
    ("namaste aur dhanyavaad", "नमस्ते और धनयवाद", "hi"),
]


@dataclass
class AccuracyResult:
    """Result of transcription accuracy test."""
    input_text: str
    expected_output: str
    actual_output: str
    language: str
    wer: float  # Word Error Rate
    cer: float  # Character Error Rate
    passed: bool
    denoising_enabled: bool
    error_message: Optional[str] = None


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER) using Levenshtein distance.
    """
    import re
    def clean_text(t: str) -> str:
        # Remove leading numbers and punctuation (e.g., "92, ")
        t = re.sub(r'^\d+[\s,.:|_-]+', '', t.strip())
        # Remove trailing numbers
        t = re.sub(r'[\s,.:|_-]+\d+$', '', t)
        return t.lower()

    ref_words = clean_text(reference).split()
    hyp_words = clean_text(hypothesis).split()
    
    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0
    
    # Build distance matrix
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j
    
    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i-1] == hyp_words[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min(
                    d[i-1][j] + 1,     # deletion
                    d[i][j-1] + 1,     # insertion
                    d[i-1][j-1] + 1    # substitution
                )
    
    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


def calculate_cer(reference: str, hypothesis: str) -> float:
    """
    Calculate Character Error Rate (CER) using Levenshtein distance.
    """
    # Clean text to remove common metadata markers like "92, " or "sent_1: "
    import re
    def clean_text(t: str) -> str:
        # Remove leading numbers and punctuation (e.g., "92, ")
        t = re.sub(r'^\d+[\s,.:|_-]+', '', t.strip())
        # Remove trailing numbers
        t = re.sub(r'[\s,.:|_-]+\d+$', '', t)
        return t.lower().replace(" ", "")

    ref_chars = list(clean_text(reference))
    hyp_chars = list(clean_text(hypothesis))
    
    if len(ref_chars) == 0:
        return 0.0 if len(hyp_chars) == 0 else 1.0
    
    # Build distance matrix
    d = [[0] * (len(hyp_chars) + 1) for _ in range(len(ref_chars) + 1)]
    
    for i in range(len(ref_chars) + 1):
        d[i][0] = i
    for j in range(len(hyp_chars) + 1):
        d[0][j] = j
    
    for i in range(1, len(ref_chars) + 1):
        for j in range(1, len(hyp_chars) + 1):
            if ref_chars[i-1] == hyp_chars[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min(
                    d[i-1][j] + 1,
                    d[i][j-1] + 1,
                    d[i-1][j-1] + 1
                )
    
    return d[len(ref_chars)][len(hyp_chars)] / len(ref_chars)


def generate_tts_audio(text: str, language: str = "pa", output_path: Optional[Path] = None) -> Path:
    """
    Generate audio from text using gTTS.
    
    Args:
        text: Text to convert to speech
        language: Language code (pa=Punjabi, en=English, hi=Hindi)
        output_path: Optional output path, generates temp file if None
        
    Returns:
        Path to generated audio file
    """
    try:
        from gtts import gTTS
    except ImportError:
        raise ImportError("gTTS not installed. Install with: pip install gtts")
    
    # Map language codes
    lang_map = {
        "pa": "pa",  # Punjabi
        "en": "en",  # English  
        "hi": "hi",  # Hindi
    }
    
    gtts_lang = lang_map.get(language, "en")
    
    # Generate audio
    tts = gTTS(text=text, lang=gtts_lang, slow=False)
    
    if output_path is None:
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            output_path = Path(tmp.name)
    
    tts.save(str(output_path))
    logger.info(f"Generated TTS audio: {output_path} (lang={gtts_lang}, text='{text[:50]}...')")
    
    return output_path


def transcribe_with_options(
    audio_path: Path,
    enable_denoising: bool = False,
    denoise_strength: str = "medium"
) -> Tuple[str, dict]:
    """
    Transcribe audio file with configurable options.
    
    Args:
        audio_path: Path to audio file
        enable_denoising: Whether to enable audio denoising
        denoise_strength: Denoising strength (light, medium, aggressive)
        
    Returns:
        Tuple of (transcribed_text, metrics_dict)
    """
    from core.orchestrator import Orchestrator
    
    # Create orchestrator
    orch = Orchestrator()
    
    # Configure processing options
    processing_options = {
        "denoiseEnabled": enable_denoising,
        "denoiseStrength": denoise_strength,
        "vadAggressiveness": 2,
        "vadMinChunkDuration": 0.5,
        "vadMaxChunkDuration": 15.0,
    }
    
    # Run transcription
    result = orch.transcribe_file(
        audio_path,
        mode="batch",
        processing_options=processing_options
    )
    
    # Extract text (prefer gurmukhi, fall back to segment text)
    transcribed_text = result.transcription.get("gurmukhi", "")
    if not transcribed_text:
        transcribed_text = " ".join(seg.text for seg in result.segments)
    
    return transcribed_text, result.metrics


def run_accuracy_test(
    input_text: str,
    expected_output: str,
    language: str,
    enable_denoising: bool = False
) -> AccuracyResult:
    """
    Run a single accuracy test.
    
    Args:
        input_text: Text to convert to speech via TTS
        expected_output: Expected transcription output
        language: Language code for TTS
        enable_denoising: Whether to enable denoising
        
    Returns:
        AccuracyResult with WER, CER, and pass/fail status
    """
    audio_path = None
    
    try:
        # Generate TTS audio
        audio_path = generate_tts_audio(input_text, language)
        
        # Transcribe with options
        actual_output, metrics = transcribe_with_options(
            audio_path,
            enable_denoising=enable_denoising
        )
        
        # Calculate accuracy metrics
        wer = calculate_wer(expected_output, actual_output)
        cer = calculate_cer(expected_output, actual_output)
        
        # Define pass threshold (WER < 50% is considered passing for TTS test)
        passed = wer < 0.5
        
        return AccuracyResult(
            input_text=input_text,
            expected_output=expected_output,
            actual_output=actual_output,
            language=language,
            wer=wer,
            cer=cer,
            passed=passed,
            denoising_enabled=enable_denoising
        )
        
    except Exception as e:
        logger.error(f"Accuracy test failed: {e}")
        return AccuracyResult(
            input_text=input_text,
            expected_output=expected_output,
            actual_output="",
            language=language,
            wer=1.0,
            cer=1.0,
            passed=False,
            denoising_enabled=enable_denoising,
            error_message=str(e)
        )
        
    finally:
        # Cleanup temp audio file
        if audio_path and audio_path.exists():
            try:
                audio_path.unlink()
            except Exception:
                pass


class TestTranscriptionAccuracy(unittest.TestCase):
    """Test transcription accuracy with TTS-generated audio."""
    
    @classmethod
    def setUpClass(cls):
        """Check for gTTS availability."""
        try:
            import gtts
            cls.gtts_available = True
        except ImportError:
            cls.gtts_available = False
            print("WARNING: gTTS not available. Install with: pip install gtts")
    
    def test_gtts_installation(self):
        """Verify gTTS is installed."""
        self.assertTrue(
            self.gtts_available,
            "gTTS is required for accuracy tests. Install with: pip install gtts"
        )
    
    def test_wer_calculation(self):
        """Test WER calculation logic."""
        # Perfect match
        self.assertEqual(calculate_wer("hello world", "hello world"), 0.0)
        
        # One substitution in two words = 50% WER
        self.assertEqual(calculate_wer("hello world", "hello there"), 0.5)
        
        # All different = 100% WER
        self.assertEqual(calculate_wer("hello world", "foo bar"), 1.0)
    
    def test_cer_calculation(self):
        """Test CER calculation logic."""
        # Perfect match
        self.assertEqual(calculate_cer("hello", "hello"), 0.0)
        
        # One char different
        self.assertAlmostEqual(calculate_cer("hello", "hallo"), 0.2, places=1)
    
    @unittest.skipUnless(True, "gTTS required")  # Will skip if gtts not available at runtime
    def test_english_phrase_accuracy(self):
        """Test accuracy on simple English phrase."""
        if not self.gtts_available:
            self.skipTest("gTTS not available")
        
        result = run_accuracy_test(
            input_text="This is a test",
            expected_output="This is a test",
            language="en",
            enable_denoising=False
        )
        
        print(f"\nEnglish Test Result:")
        print(f"  Input: {result.input_text}")
        print(f"  Expected: {result.expected_output}")
        print(f"  Actual: {result.actual_output}")
        print(f"  WER: {result.wer:.2%}")
        print(f"  CER: {result.cer:.2%}")
        
        # English should have reasonable accuracy
        self.assertLess(result.wer, 0.75, f"WER too high: {result.wer:.2%}")
    
    @unittest.skipUnless(True, "gTTS required")
    def test_denoising_comparison(self):
        """Compare transcription with and without denoising."""
        if not self.gtts_available:
            self.skipTest("gTTS not available")
        
        test_text = "hello how are you today"
        expected = "hello how are you today"
        
        # Test without denoising
        result_no_denoise = run_accuracy_test(
            input_text=test_text,
            expected_output=expected,
            language="en",
            enable_denoising=False
        )
        
        # Test with denoising
        result_with_denoise = run_accuracy_test(
            input_text=test_text,
            expected_output=expected,
            language="en",
            enable_denoising=True
        )
        
        print(f"\nDenoising Comparison:")
        print(f"  Without denoising - WER: {result_no_denoise.wer:.2%}")
        print(f"  With denoising    - WER: {result_with_denoise.wer:.2%}")
        
        # Just verify both ran without error
        self.assertIsNone(result_no_denoise.error_message)


def run_full_benchmark(enable_denoising: bool = False):
    """
    Run full accuracy benchmark on all test phrases.
    
    Args:
        enable_denoising: Whether to enable denoising
        
    Returns:
        List of AccuracyResult
    """
    results = []
    
    print(f"\n{'='*60}")
    print(f"Running Transcription Accuracy Benchmark")
    print(f"Denoising: {'ENABLED' if enable_denoising else 'DISABLED'}")
    print(f"{'='*60}\n")
    
    for input_text, expected, language in TEST_PHRASES:
        print(f"Testing: '{input_text[:40]}...' (lang={language})")
        
        result = run_accuracy_test(
            input_text=input_text,
            expected_output=expected,
            language=language,
            enable_denoising=enable_denoising
        )
        
        results.append(result)
        
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {status} | WER: {result.wer:.2%} | CER: {result.cer:.2%}")
        
        if result.error_message:
            print(f"  ERROR: {result.error_message}")
        elif not result.passed:
            print(f"  Expected: {result.expected_output[:50]}...")
            print(f"  Actual:   {result.actual_output[:50]}...")
        
        print()
    
    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_wer = sum(r.wer for r in results) / len(results) if results else 0
    avg_cer = sum(r.cer for r in results) / len(results) if results else 0
    
    print(f"{'='*60}")
    print(f"SUMMARY: {passed}/{total} tests passed")
    print(f"Average WER: {avg_wer:.2%}")
    print(f"Average CER: {avg_cer:.2%}")
    print(f"{'='*60}\n")
    
    return results




# =============================================================================
# Kaggle Punjabi Speech Recognition Dataset Support
# =============================================================================

def download_kaggle_dataset(manual_path: Optional[Path] = None) -> Path:
    """
    Download the Kaggle Punjabi Speech Recognition dataset or use manual path.
    
    Args:
        manual_path: Optional manual path to dataset
        
    Returns:
        Path to dataset directory
    """
    if manual_path:
        if not manual_path.exists():
            raise FileNotFoundError(f"Manual Kaggle path does not exist: {manual_path}")
        return manual_path

    try:
        import kagglehub
    except ImportError:
        raise ImportError("kagglehub not installed and no manual path provided. Install with: pip install kagglehub")
    
    print("Downloading Kaggle Punjabi Speech Recognition dataset...")
    path = kagglehub.dataset_download("warcoder/punjabi-speech-recognition")
    print(f"Dataset downloaded to: {path}")
    
    return Path(path)


def load_kaggle_samples(dataset_path: Path, num_samples: int = 10) -> List[Tuple[Path, str]]:
    """
    Load audio file paths and their transcriptions from Kaggle dataset.
    
    Args:
        dataset_path: Path to downloaded dataset
        num_samples: Number of samples to load
        
    Returns:
        List of (audio_path, expected_transcription) tuples
    """
    # If the directory contains exactly one subdirectory, dive into it
    # This handles nested structures like 'versions/1/punjabi/'
    subdirs = [d for d in dataset_path.iterdir() if d.is_dir()]
    if len(subdirs) == 1 and not (dataset_path / "metadata.csv").exists():
        logger.info(f"Diving into subdirectory: {subdirs[0].name}")
        dataset_path = subdirs[0]

    samples = []
    audio_extensions = ['.wav', '.mp3', '.flac', '.ogg']
    transcript_extensions = ['.txt', '.wrd', '.lab', '.transcript']
    
    # Recursively find ALL CSV/TSV files in the dataset
    metadata_files = list(dataset_path.rglob('*.csv')) + list(dataset_path.rglob('*.tsv'))
    logger.info(f"Found {len(metadata_files)} metadata files recursively")
    
    if metadata_files:
        # Sort to prioritize certain names
        metadata_files.sort(key=lambda p: (
            0 if "metadata" in p.name.lower() else 
            1 if "train" in p.name.lower() else 
            2 if "test" in p.name.lower() else 3
        ))
        
        for metadata_file in metadata_files:
            logger.info(f"Trying metadata file: {metadata_file}")
            delimiter = '\t' if metadata_file.suffix == '.tsv' else ','
            
            try:
                # Check for Fairseq style sidecar files
                transcript_file = None
                # Check for basenames (train.tsv -> train.wrd)
                for ext in ['.wrd', '.txt', '.ltr', '.transcript']:
                    sidecar = metadata_file.with_suffix(ext)
                    if sidecar.exists():
                        transcript_file = sidecar
                        break
                
                # If not found, look for ANY .wrd or .txt in the same directory if there's only one
                if not transcript_file:
                    alternatives = list(metadata_file.parent.glob('*.wrd')) + list(metadata_file.parent.glob('*.txt'))
                    if len(alternatives) == 1:
                        transcript_file = alternatives[0]

                with open(metadata_file, 'r', encoding='utf-8') as f:
                    # Fairseq manifest detection: Line 1 is a directory path
                    first_line = f.readline().strip()
                    f.seek(0)
                    
                    # Detect Fairseq: delimiter is \t, first line has / or \, and no headers
                    is_fairseq = (
                        delimiter == '\t' and 
                        ('/' in first_line or '\\' in first_line) and 
                        not any(h in first_line.lower() for h in ['path', 'audio', 'file'])
                    )

                    if is_fairseq:
                        logger.info(f"Detected Fairseq manifest: {metadata_file}")
                        # Root path provided in the manifest (first line)
                        manifest_root = Path(first_line)
                        lines = f.readlines()[1:] # Skip root path line
                        
                        if transcript_file:
                            logger.info(f"Using transcription file: {transcript_file}")
                            with open(transcript_file, 'r', encoding='utf-8') as tf:
                                transcripts = [l.strip() for l in tf.readlines()]
                            
                            for i, line in enumerate(lines):
                                if len(samples) >= num_samples: break
                                parts = line.split('\t')
                                rel_path = parts[0]
                                
                                # Try multiple resolutions for audio
                                pts = [
                                    manifest_root / rel_path,
                                    dataset_path / rel_path,
                                    metadata_file.parent / rel_path,
                                    dataset_path / "Audio files" / Path(rel_path).name,
                                ]
                                
                                # Add extensions if missing
                                if not any(rel_path.endswith(ext) for ext in audio_extensions):
                                    for ext in audio_extensions:
                                        pts.extend([p.with_suffix(ext) for p in pts if p.suffix == ""])

                                for audio_path in pts:
                                    if audio_path.exists() and audio_path.is_file():
                                        if i < len(transcripts):
                                            samples.append((audio_path, transcripts[i]))
                                            break
                        else:
                            logger.warning(f"Found Fairseq manifest but no transcription file for {metadata_file}")
                        continue

                    # Regular CSV/TSV processing
                    reader = csv.DictReader(f, delimiter=delimiter)
                    
                    for i, row in enumerate(reader):
                        if len(samples) >= num_samples:
                            break
                        
                        # Find audio column
                        audio_col = None
                        for col in ['path', 'audio', 'file', 'filename', 'audio_path', 'audio_id', 'id']:
                            if col in row:
                                audio_col = col
                                break
                        
                        # Find text column
                        text_col = None
                        for col in ['sentence', 'text', 'transcript', 'transcription', 'label', 'punjabi', 'gurmukhi']:
                            if col in row:
                                text_col = col
                                break
                        
                        if audio_col and text_col:
                            # Try different path resolutions for audio
                            val = row[audio_col]
                            # Possible paths: relative to CSV, relative to dataset root, or just filename
                            potential_paths = [
                                metadata_file.parent / val,
                                dataset_path / val,
                                dataset_path / "audio" / val,
                                dataset_path / "punjabi" / val,
                                dataset_path / "Audio files" / val,
                            ]
                            
                            # Add extensions if missing
                            if not any(val.endswith(ext) for ext in audio_extensions):
                                for ext in audio_extensions:
                                    potential_paths.extend([p.with_suffix(ext) for p in potential_paths if p.suffix == ""])

                            for audio_path in potential_paths:
                                if audio_path.exists() and audio_path.is_file():
                                    samples.append((audio_path, row[text_col]))
                                    break
            except Exception as e:
                logger.warning(f"Error reading {metadata_file}: {e}")
                continue
            
            if len(samples) >= num_samples:
                break
    
    # Fallback: Search for paired .txt/wrd and audio files recursively
    if not samples:
        logger.info("Falling back to recursive paired file search")
        for ext in audio_extensions:
            audio_files = list(dataset_path.rglob(f'*{ext}'))[:num_samples*2]
            for audio_file in audio_files:
                if len(samples) >= num_samples:
                    break
                
                # Try specific transcript extensions with same basename
                found_match = False
                for t_ext in transcript_extensions:
                    text_file = audio_file.with_suffix(t_ext)
                    if text_file.exists():
                        with open(text_file, 'r', encoding='utf-8') as f:
                            samples.append((audio_file, f.read().strip()))
                        found_match = True
                        break
                
                if found_match: continue

                # Look for ONE transcript file in the same directory that might be a manifest
                # But only if it has a sensible name (e.g., matching the directory)
                txt_files = []
                for t_ext in transcript_extensions:
                    txt_files.extend(list(audio_file.parent.glob(f'*{t_ext}')))
                
                if len(txt_files) == 1:
                    # Check if the filename contains the audio filename
                    if audio_file.stem in txt_files[0].stem or txt_files[0].stem in audio_file.stem:
                        with open(txt_files[0], 'r', encoding='utf-8') as f:
                            samples.append((audio_file, f.read().strip()))
                    else:
                        # Possibly a shared manifest for the directory. 
                        # Only use it if it's the only one AND it's not huge
                        with open(txt_files[0], 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if len(content.splitlines()) < 2: # Only if it's a single line
                                samples.append((audio_file, content))

            if samples: break

    if not samples:
        logger.warning(f"No audio-transcription pairs found in {dataset_path}")
        # Help user debug by listing some files
        print(f"\nDebug - Files found in {dataset_path}:")
        all_items = list(dataset_path.iterdir())
        for item in all_items[:20]:
            print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
        if len(all_items) > 20:
            print(f"  ... and {len(all_items)-20} more")
    
    return samples[:num_samples]


def run_kaggle_benchmark(num_samples: int = 10, enable_denoising: bool = False, manual_path: Optional[Path] = None) -> List[AccuracyResult]:
    """
    Run accuracy benchmark using Kaggle Punjabi Speech dataset.
    
    Args:
        num_samples: Number of samples to test
        enable_denoising: Whether to enable denoising
        manual_path: Optional manual path to dataset
        
    Returns:
        List of AccuracyResult
    """
    from core.orchestrator import Orchestrator
    
    # Download dataset or use manual path
    try:
        dataset_path = download_kaggle_dataset(manual_path)
    except Exception as e:
        print(f"ERROR: {e}")
        return []
    
    # Load samples
    samples = load_kaggle_samples(dataset_path, num_samples)
    
    if not samples:
        print("ERROR: Could not load any samples from Kaggle dataset")
        return []
    
    print(f"\n{'='*60}")
    print(f"Running Kaggle Punjabi Speech Accuracy Benchmark")
    print(f"Samples: {len(samples)} | Denoising: {'ENABLED' if enable_denoising else 'DISABLED'}")
    print(f"{'='*60}\n")
    
    results = []
    orch = Orchestrator()
    
    for i, (audio_path, expected) in enumerate(samples):
        print(f"[{i+1}/{len(samples)}] Testing: {audio_path.name}")
        
        try:
            processing_options = {
                "denoiseEnabled": enable_denoising,
                "denoiseStrength": "medium",
            }
            
            result = orch.transcribe_file(
                audio_path,
                mode="batch",
                processing_options=processing_options
            )
            
            # Get transcribed text
            actual = result.transcription.get("gurmukhi", "")
            if not actual:
                actual = " ".join(seg.text for seg in result.segments)
            
            # Calculate accuracy
            wer = calculate_wer(expected, actual)
            cer = calculate_cer(expected, actual)
            passed = wer < 0.5
            
            acc_result = AccuracyResult(
                input_text=str(audio_path.name),
                expected_output=expected[:100],
                actual_output=actual[:100],
                language="pa",
                wer=wer,
                cer=cer,
                passed=passed,
                denoising_enabled=enable_denoising
            )
            results.append(acc_result)
            
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status} | WER: {wer:.2%} | CER: {cer:.2%}")
            
            if not passed:
                print(f"  Expected: {expected[:60]}...")
                print(f"  Actual:   {actual[:60]}...")
            print()
            
        except Exception as e:
            logger.error(f"Failed to process {audio_path}: {e}")
            results.append(AccuracyResult(
                input_text=str(audio_path.name),
                expected_output=expected[:100],
                actual_output="",
                language="pa",
                wer=1.0,
                cer=1.0,
                passed=False,
                denoising_enabled=enable_denoising,
                error_message=str(e)
            ))
            print(f"  ✗ ERROR: {e}\n")
    
    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_wer = sum(r.wer for r in results) / len(results) if results else 0
    avg_cer = sum(r.cer for r in results) / len(results) if results else 0
    
    print(f"{'='*60}")
    print(f"KAGGLE DATASET SUMMARY: {passed}/{total} tests passed")
    print(f"Average WER: {avg_wer:.2%}")
    print(f"Average CER: {avg_cer:.2%}")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run transcription accuracy tests")
    parser.add_argument("--denoise", action="store_true", help="Enable denoising")
    parser.add_argument("--unittest", action="store_true", help="Run as unittest suite")
    parser.add_argument("--kaggle", action="store_true", help="Use Kaggle Punjabi dataset (requires kagglehub)")
    parser.add_argument("--kaggle-path", type=str, help="Manual path to Kaggle dataset root")
    parser.add_argument("--kaggle-samples", type=int, default=10, help="Number of Kaggle samples to test")
    args = parser.parse_args()
    
    if args.unittest:
        unittest.main(argv=[''], exit=False, verbosity=2)
    elif args.kaggle:
        # Run with Kaggle dataset
        path = Path(args.kaggle_path) if args.kaggle_path else None
        run_kaggle_benchmark(
            num_samples=args.kaggle_samples, 
            enable_denoising=args.denoise,
            manual_path=path
        )
    else:
        # Run full TTS benchmark
        run_full_benchmark(enable_denoising=args.denoise)

