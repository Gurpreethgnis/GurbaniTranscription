"""
WER/CER Reports for Transcription Accuracy.

Calculates Word Error Rate (WER) and Character Error Rate (CER) using jiwer.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
import csv
import json
from datetime import datetime

try:
    import jiwer
    JIWER_AVAILABLE = True
except ImportError:
    JIWER_AVAILABLE = False
    logging.warning("jiwer not available. Install with: pip install jiwer")

from models import TranscriptionResult, ProcessedSegment

logger = logging.getLogger(__name__)


def calculate_wer_cer(
    predicted: TranscriptionResult,
    ground_truth: Dict[str, Any],
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate WER and CER for a transcription result against ground truth.
    
    Args:
        predicted: TranscriptionResult from the system
        ground_truth: Ground truth data dictionary
        language: Optional language filter ('pa', 'en', etc.)
    
    Returns:
        Dictionary with WER, CER, and detailed metrics
    """
    if not JIWER_AVAILABLE:
        raise ImportError("jiwer is required for WER/CER calculation. Install with: pip install jiwer")
    
    # Align predicted segments with ground truth segments
    aligned_pairs = _align_segments(predicted.segments, ground_truth['segments'])
    
    # Calculate per-segment metrics
    segment_metrics = []
    total_substitutions = 0
    total_insertions = 0
    total_deletions = 0
    total_words = 0
    total_chars = 0
    total_char_errors = 0
    
    for pred_seg, gt_seg in aligned_pairs:
        if gt_seg is None:
            # Predicted segment with no ground truth (insertion)
            continue
        
        # Filter by language if specified
        if language and pred_seg.language != language:
            continue
        
        pred_text = pred_seg.text.strip()
        gt_text = gt_seg.get('ground_truth_gurmukhi', '').strip()
        
        if not gt_text:
            continue
        
        # Calculate WER
        wer_metrics = jiwer.compute_measures(gt_text, pred_text)
        wer = wer_metrics['wer']
        substitutions = wer_metrics['substitutions']
        insertions = wer_metrics['insertions']
        deletions = wer_metrics['deletions']
        hits = wer_metrics['hits']
        
        total_substitutions += substitutions
        total_insertions += insertions
        total_deletions += deletions
        total_words += len(gt_text.split())
        
        # Calculate CER (character-level)
        cer_metrics = jiwer.compute_measures(
            list(gt_text),
            list(pred_text),
            truth_transform=jiwer.wer_default,
            hypothesis_transform=jiwer.wer_default
        )
        cer = cer_metrics['wer']  # WER at character level is CER
        char_errors = cer_metrics['substitutions'] + cer_metrics['insertions'] + cer_metrics['deletions']
        total_char_errors += char_errors
        total_chars += len(gt_text)
        
        segment_metrics.append({
            'start': pred_seg.start,
            'end': pred_seg.end,
            'wer': wer,
            'cer': cer,
            'substitutions': substitutions,
            'insertions': insertions,
            'deletions': deletions,
            'hits': hits,
            'char_errors': char_errors,
            'predicted_text': pred_text,
            'ground_truth_text': gt_text,
            'confidence': pred_seg.confidence,
            'language': pred_seg.language
        })
    
    # Calculate overall metrics
    overall_wer = (
        (total_substitutions + total_insertions + total_deletions) / total_words
        if total_words > 0 else 0.0
    )
    
    overall_cer = (
        total_char_errors / total_chars
        if total_chars > 0 else 0.0
    )
    
    # Per-language breakdown
    language_breakdown = {}
    for seg_metric in segment_metrics:
        lang = seg_metric['language']
        if lang not in language_breakdown:
            language_breakdown[lang] = {
                'wer_sum': 0.0,
                'cer_sum': 0.0,
                'count': 0,
                'total_words': 0,
                'total_chars': 0,
                'total_char_errors': 0
            }
        
        lang_metrics = language_breakdown[lang]
        lang_metrics['wer_sum'] += seg_metric['wer']
        lang_metrics['cer_sum'] += seg_metric['cer']
        lang_metrics['count'] += 1
        lang_metrics['total_words'] += len(seg_metric['ground_truth_text'].split())
        lang_metrics['total_chars'] += len(seg_metric['ground_truth_text'])
        lang_metrics['total_char_errors'] += seg_metric['char_errors']
    
    # Calculate per-language averages
    for lang, metrics in language_breakdown.items():
        if metrics['count'] > 0:
            metrics['avg_wer'] = metrics['wer_sum'] / metrics['count']
            metrics['avg_cer'] = metrics['cer_sum'] / metrics['count']
        else:
            metrics['avg_wer'] = 0.0
            metrics['avg_cer'] = 0.0
        
        if metrics['total_words'] > 0:
            metrics['overall_wer'] = (
                (metrics.get('substitutions', 0) + metrics.get('insertions', 0) + metrics.get('deletions', 0))
                / metrics['total_words']
            )
        else:
            metrics['overall_wer'] = 0.0
        
        if metrics['total_chars'] > 0:
            metrics['overall_cer'] = metrics['total_char_errors'] / metrics['total_chars']
        else:
            metrics['overall_cer'] = 0.0
    
    # Confidence-weighted metrics
    confidence_weighted_wer = 0.0
    confidence_weighted_cer = 0.0
    total_confidence = 0.0
    
    for seg_metric in segment_metrics:
        conf = seg_metric['confidence']
        confidence_weighted_wer += seg_metric['wer'] * conf
        confidence_weighted_cer += seg_metric['cer'] * conf
        total_confidence += conf
    
    if total_confidence > 0:
        confidence_weighted_wer /= total_confidence
        confidence_weighted_cer /= total_confidence
    
    return {
        'overall_wer': overall_wer,
        'overall_cer': overall_cer,
        'total_segments': len(segment_metrics),
        'total_words': total_words,
        'total_chars': total_chars,
        'total_substitutions': total_substitutions,
        'total_insertions': total_insertions,
        'total_deletions': total_deletions,
        'confidence_weighted_wer': confidence_weighted_wer,
        'confidence_weighted_cer': confidence_weighted_cer,
        'language_breakdown': language_breakdown,
        'segment_metrics': segment_metrics
    }


def _align_segments(
    predicted_segments: List[ProcessedSegment],
    ground_truth_segments: List[Dict[str, Any]]
) -> List[tuple]:
    """
    Align predicted segments with ground truth segments by timestamp.
    
    Args:
        predicted_segments: List of ProcessedSegment from transcription
        ground_truth_segments: List of ground truth segment dictionaries
    
    Returns:
        List of (predicted_segment, ground_truth_segment) tuples
    """
    aligned = []
    gt_index = 0
    
    for pred_seg in predicted_segments:
        best_gt = None
        best_overlap = 0.0
        
        # Find ground truth segment with best overlap
        for i, gt_seg in enumerate(ground_truth_segments[gt_index:], start=gt_index):
            gt_start = gt_seg['start']
            gt_end = gt_seg['end']
            
            # Calculate overlap
            overlap_start = max(pred_seg.start, gt_start)
            overlap_end = min(pred_seg.end, gt_end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > best_overlap:
                best_overlap = overlap
                best_gt = gt_seg
                gt_index = i
        
        aligned.append((pred_seg, best_gt))
    
    return aligned


def generate_report(
    results: List[Dict[str, Any]],
    output_path: Path,
    format: str = "json"
) -> Path:
    """
    Generate WER/CER report from multiple evaluation results.
    
    Args:
        results: List of evaluation result dictionaries
        output_path: Path to save report
        format: Report format ("json", "text", "csv")
    
    Returns:
        Path to generated report
    """
    if format == "json":
        return _generate_json_report(results, output_path)
    elif format == "text":
        return _generate_text_report(results, output_path)
    elif format == "csv":
        return _generate_csv_report(results, output_path)
    else:
        raise ValueError(f"Unknown format: {format}")


def _generate_json_report(
    results: List[Dict[str, Any]],
    output_path: Path
) -> Path:
    """Generate JSON report."""
    report = {
        'generated_at': datetime.now().isoformat(),
        'total_files': len(results),
        'results': results,
        'summary': {
            'avg_wer': sum(r['overall_wer'] for r in results) / len(results) if results else 0.0,
            'avg_cer': sum(r['overall_cer'] for r in results) / len(results) if results else 0.0,
            'total_segments': sum(r['total_segments'] for r in results),
            'total_words': sum(r['total_words'] for r in results)
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Generated JSON report: {output_path}")
    return output_path


def _generate_text_report(
    results: List[Dict[str, Any]],
    output_path: Path
) -> Path:
    """Generate human-readable text report."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("WER/CER Evaluation Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total Files: {len(results)}\n\n")
        
        # Overall summary
        if results:
            avg_wer = sum(r['overall_wer'] for r in results) / len(results)
            avg_cer = sum(r['overall_cer'] for r in results) / len(results)
            total_segments = sum(r['total_segments'] for r in results)
            total_words = sum(r['total_words'] for r in results)
            
            f.write("Overall Summary:\n")
            f.write(f"  Average WER: {avg_wer:.4f} ({avg_wer*100:.2f}%)\n")
            f.write(f"  Average CER: {avg_cer:.4f} ({avg_cer*100:.2f}%)\n")
            f.write(f"  Total Segments: {total_segments}\n")
            f.write(f"  Total Words: {total_words}\n\n")
        
        # Per-file breakdown
        f.write("-" * 80 + "\n")
        f.write("Per-File Results:\n")
        f.write("-" * 80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"File {i}:\n")
            f.write(f"  WER: {result['overall_wer']:.4f} ({result['overall_wer']*100:.2f}%)\n")
            f.write(f"  CER: {result['overall_cer']:.4f} ({result['overall_cer']*100:.2f}%)\n")
            f.write(f"  Segments: {result['total_segments']}\n")
            f.write(f"  Words: {result['total_words']}\n")
            f.write(f"  Substitutions: {result['total_substitutions']}\n")
            f.write(f"  Insertions: {result['total_insertions']}\n")
            f.write(f"  Deletions: {result['total_deletions']}\n")
            
            # Language breakdown
            if result['language_breakdown']:
                f.write("  Language Breakdown:\n")
                for lang, metrics in result['language_breakdown'].items():
                    f.write(f"    {lang}:\n")
                    f.write(f"      WER: {metrics['overall_wer']:.4f}\n")
                    f.write(f"      CER: {metrics['overall_cer']:.4f}\n")
                    f.write(f"      Segments: {metrics['count']}\n")
            f.write("\n")
    
    logger.info(f"Generated text report: {output_path}")
    return output_path


def _generate_csv_report(
    results: List[Dict[str, Any]],
    output_path: Path
) -> Path:
    """Generate CSV report for analysis."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow([
            'file_index', 'segment_start', 'segment_end', 'wer', 'cer',
            'substitutions', 'insertions', 'deletions', 'hits',
            'char_errors', 'confidence', 'language',
            'predicted_text', 'ground_truth_text'
        ])
        
        # Data rows
        for file_idx, result in enumerate(results):
            for seg_metric in result['segment_metrics']:
                writer.writerow([
                    file_idx,
                    seg_metric['start'],
                    seg_metric['end'],
                    seg_metric['wer'],
                    seg_metric['cer'],
                    seg_metric['substitutions'],
                    seg_metric['insertions'],
                    seg_metric['deletions'],
                    seg_metric['hits'],
                    seg_metric['char_errors'],
                    seg_metric['confidence'],
                    seg_metric['language'],
                    seg_metric['predicted_text'],
                    seg_metric['ground_truth_text']
                ])
    
    logger.info(f"Generated CSV report: {output_path}")
    return output_path
