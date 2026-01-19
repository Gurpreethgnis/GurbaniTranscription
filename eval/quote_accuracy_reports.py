"""
Quote Accuracy Reports.

Measures quote detection and canonical replacement accuracy.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime

from core.models import TranscriptionResult, ProcessedSegment, QuoteMatch

logger = logging.getLogger(__name__)


def calculate_quote_metrics(
    predicted: TranscriptionResult,
    ground_truth: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate quote detection and canonical replacement accuracy metrics.
    
    Args:
        predicted: TranscriptionResult from the system
        ground_truth: Ground truth data dictionary with quote annotations
    
    Returns:
        Dictionary with precision, recall, F1, and detailed metrics
    """
    # Extract predicted quotes
    predicted_quotes = []
    for seg in predicted.segments:
        if seg.quote_match is not None:
            predicted_quotes.append({
                'segment': seg,
                'quote_match': seg.quote_match,
                'start': seg.start,
                'end': seg.end
            })
    
    # Extract ground truth quotes
    ground_truth_quotes = []
    for gt_seg in ground_truth.get('segments', []):
        if 'quotes' in gt_seg:
            for quote in gt_seg['quotes']:
                ground_truth_quotes.append({
                    'segment_start': gt_seg['start'],
                    'segment_end': gt_seg['end'],
                    'quote_start': quote['start'],
                    'quote_end': quote['end'],
                    'canonical_line_id': quote['canonical_line_id'],
                    'expected_ang': quote.get('expected_ang'),
                    'expected_source': quote.get('expected_source')
                })
    
    # Match predicted quotes with ground truth quotes
    matches = _match_quotes(predicted_quotes, ground_truth_quotes)
    
    # Calculate metrics
    true_positives = len([m for m in matches if m['is_match']])
    false_positives = len(predicted_quotes) - true_positives
    false_negatives = len(ground_truth_quotes) - true_positives
    
    # Precision, Recall, F1
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0 else 0.0
    )
    
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0 else 0.0
    )
    
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0 else 0.0
    )
    
    # Canonical replacement accuracy
    correct_replacements = 0
    total_replacements = 0
    
    for match in matches:
        if match['is_match']:
            total_replacements += 1
            pred_quote = match['predicted']
            gt_quote = match['ground_truth']
            
            # Check if canonical line ID matches
            if pred_quote['quote_match'].line_id == gt_quote['canonical_line_id']:
                correct_replacements += 1
                match['correct_replacement'] = True
            else:
                match['correct_replacement'] = False
                
                # Check if Ang matches (if available)
                if (pred_quote['quote_match'].ang is not None and
                    gt_quote['expected_ang'] is not None):
                    if pred_quote['quote_match'].ang == gt_quote['expected_ang']:
                        match['ang_match'] = True
                    else:
                        match['ang_match'] = False
    
    replacement_accuracy = (
        correct_replacements / total_replacements
        if total_replacements > 0 else 0.0
    )
    
    # Per-confidence-threshold analysis
    confidence_thresholds = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    threshold_metrics = {}
    
    for threshold in confidence_thresholds:
        filtered_pred = [q for q in predicted_quotes if q['quote_match'].confidence >= threshold]
        filtered_matches = _match_quotes(filtered_pred, ground_truth_quotes)
        
        tp = len([m for m in filtered_matches if m['is_match']])
        fp = len(filtered_pred) - tp
        fn = len(ground_truth_quotes) - tp
        
        thresh_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        thresh_recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        thresh_f1 = (
            2 * (thresh_precision * thresh_recall) / (thresh_precision + thresh_recall)
            if (thresh_precision + thresh_recall) > 0 else 0.0
        )
        
        threshold_metrics[threshold] = {
            'precision': thresh_precision,
            'recall': thresh_recall,
            'f1': thresh_f1,
            'true_positives': tp,
            'false_positives': fp,
            'false_negatives': fn
        }
    
    # Per-source breakdown
    source_breakdown = {}
    for match in matches:
        if match['is_match']:
            source = match['predicted']['quote_match'].source.value
            if source not in source_breakdown:
                source_breakdown[source] = {
                    'true_positives': 0,
                    'false_positives': 0,
                    'false_negatives': 0
                }
            source_breakdown[source]['true_positives'] += 1
    
    # Count false positives/negatives per source
    for pred_quote in predicted_quotes:
        if not any(m['is_match'] and m['predicted'] == pred_quote for m in matches):
            source = pred_quote['quote_match'].source.value
            if source not in source_breakdown:
                source_breakdown[source] = {
                    'true_positives': 0,
                    'false_positives': 0,
                    'false_negatives': 0
                }
            source_breakdown[source]['false_positives'] += 1
    
    for gt_quote in ground_truth_quotes:
        if not any(m['is_match'] and m['ground_truth'] == gt_quote for m in matches):
            source = gt_quote.get('expected_source', 'Unknown')
            if source not in source_breakdown:
                source_breakdown[source] = {
                    'true_positives': 0,
                    'false_positives': 0,
                    'false_negatives': 0
                }
            source_breakdown[source]['false_negatives'] += 1
    
    # Calculate precision/recall per source
    for source, metrics in source_breakdown.items():
        tp = metrics['true_positives']
        fp = metrics['false_positives']
        fn = metrics['false_negatives']
        
        metrics['precision'] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        metrics['recall'] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        metrics['f1'] = (
            2 * (metrics['precision'] * metrics['recall']) / (metrics['precision'] + metrics['recall'])
            if (metrics['precision'] + metrics['recall']) > 0 else 0.0
        )
    
    # Collect examples
    false_positives_examples = [
        {
            'start': q['start'],
            'end': q['end'],
            'detected_line_id': q['quote_match'].line_id,
            'detected_ang': q['quote_match'].ang,
            'detected_source': q['quote_match'].source.value,
            'confidence': q['quote_match'].confidence,
            'text': q['segment'].text
        }
        for q in predicted_quotes
        if not any(m['is_match'] and m['predicted'] == q for m in matches)
    ]
    
    false_negatives_examples = [
        {
            'start': q['segment_start'] + q['quote_start'],
            'end': q['segment_start'] + q['quote_end'],
            'expected_line_id': q['canonical_line_id'],
            'expected_ang': q['expected_ang'],
            'expected_source': q['expected_source']
        }
        for q in ground_truth_quotes
        if not any(m['is_match'] and m['ground_truth'] == q for m in matches)
    ]
    
    return {
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'replacement_accuracy': replacement_accuracy,
        'correct_replacements': correct_replacements,
        'total_replacements': total_replacements,
        'threshold_metrics': threshold_metrics,
        'source_breakdown': source_breakdown,
        'false_positives_examples': false_positives_examples[:10],  # Limit to 10 examples
        'false_negatives_examples': false_negatives_examples[:10],
        'matches': matches
    }


def _match_quotes(
    predicted_quotes: List[Dict[str, Any]],
    ground_truth_quotes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Match predicted quotes with ground truth quotes by timestamp overlap.
    
    Args:
        predicted_quotes: List of predicted quote dictionaries
        ground_truth_quotes: List of ground truth quote dictionaries
    
    Returns:
        List of match dictionaries with 'predicted', 'ground_truth', 'is_match' keys
    """
    matches = []
    matched_gt_indices = set()
    
    for pred_quote in predicted_quotes:
        best_match = None
        best_overlap = 0.0
        best_gt_idx = None
        
        # Find ground truth quote with best overlap
        for gt_idx, gt_quote in enumerate(ground_truth_quotes):
            if gt_idx in matched_gt_indices:
                continue
            
            # Calculate absolute timestamps for ground truth quote
            gt_start = gt_quote['segment_start'] + gt_quote['quote_start']
            gt_end = gt_quote['segment_start'] + gt_quote['quote_end']
            
            # Calculate overlap
            overlap_start = max(pred_quote['start'], gt_start)
            overlap_end = min(pred_quote['end'], gt_end)
            overlap = max(0, overlap_end - overlap_start)
            
            # Normalize by union
            union = max(pred_quote['end'], gt_end) - min(pred_quote['start'], gt_start)
            overlap_ratio = overlap / union if union > 0 else 0.0
            
            if overlap_ratio > best_overlap and overlap_ratio > 0.5:  # Require >50% overlap
                best_overlap = overlap_ratio
                best_match = gt_quote
                best_gt_idx = gt_idx
        
        if best_match:
            matches.append({
                'predicted': pred_quote,
                'ground_truth': best_match,
                'is_match': True,
                'overlap_ratio': best_overlap
            })
            matched_gt_indices.add(best_gt_idx)
        else:
            matches.append({
                'predicted': pred_quote,
                'ground_truth': None,
                'is_match': False,
                'overlap_ratio': 0.0
            })
    
    # Add unmatched ground truth quotes as false negatives
    for gt_idx, gt_quote in enumerate(ground_truth_quotes):
        if gt_idx not in matched_gt_indices:
            matches.append({
                'predicted': None,
                'ground_truth': gt_quote,
                'is_match': False,
                'overlap_ratio': 0.0
            })
    
    return matches


def generate_quote_report(
    metrics: Dict[str, Any],
    examples: Optional[List[Dict[str, Any]]] = None,
    output_path: Path
) -> Path:
    """
    Generate quote accuracy report.
    
    Args:
        metrics: Quote metrics dictionary from calculate_quote_metrics
        examples: Optional additional examples to include
        output_path: Path to save report
    
    Returns:
        Path to generated report
    """
    report = {
        'generated_at': datetime.now().isoformat(),
        'metrics': metrics,
        'examples': examples or []
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Also generate human-readable text summary
    text_path = output_path.with_suffix('.txt')
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("Quote Detection Accuracy Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        
        f.write("Overall Metrics:\n")
        f.write(f"  Precision: {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)\n")
        f.write(f"  Recall: {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)\n")
        f.write(f"  F1 Score: {metrics['f1_score']:.4f}\n")
        f.write(f"  True Positives: {metrics['true_positives']}\n")
        f.write(f"  False Positives: {metrics['false_positives']}\n")
        f.write(f"  False Negatives: {metrics['false_negatives']}\n\n")
        
        f.write("Canonical Replacement Accuracy:\n")
        f.write(f"  Accuracy: {metrics['replacement_accuracy']:.4f} ({metrics['replacement_accuracy']*100:.2f}%)\n")
        f.write(f"  Correct Replacements: {metrics['correct_replacements']}\n")
        f.write(f"  Total Replacements: {metrics['total_replacements']}\n\n")
        
        f.write("Per-Confidence-Threshold Metrics:\n")
        for threshold, thresh_metrics in sorted(metrics['threshold_metrics'].items()):
            f.write(f"  Threshold {threshold}:\n")
            f.write(f"    Precision: {thresh_metrics['precision']:.4f}\n")
            f.write(f"    Recall: {thresh_metrics['recall']:.4f}\n")
            f.write(f"    F1: {thresh_metrics['f1']:.4f}\n")
            f.write(f"    TP: {thresh_metrics['true_positives']}, "
                   f"FP: {thresh_metrics['false_positives']}, "
                   f"FN: {thresh_metrics['false_negatives']}\n")
        f.write("\n")
        
        f.write("Per-Source Breakdown:\n")
        for source, source_metrics in metrics['source_breakdown'].items():
            f.write(f"  {source}:\n")
            f.write(f"    Precision: {source_metrics['precision']:.4f}\n")
            f.write(f"    Recall: {source_metrics['recall']:.4f}\n")
            f.write(f"    F1: {source_metrics['f1']:.4f}\n")
            f.write(f"    TP: {source_metrics['true_positives']}, "
                   f"FP: {source_metrics['false_positives']}, "
                   f"FN: {source_metrics['false_negatives']}\n")
        f.write("\n")
        
        if metrics['false_positives_examples']:
            f.write("False Positive Examples (first 10):\n")
            for i, example in enumerate(metrics['false_positives_examples'], 1):
                f.write(f"  {i}. Time: {example['start']:.2f}-{example['end']:.2f}s\n")
                f.write(f"     Line ID: {example['detected_line_id']}\n")
                f.write(f"     Ang: {example['detected_ang']}\n")
                f.write(f"     Source: {example['detected_source']}\n")
                f.write(f"     Confidence: {example['confidence']:.2f}\n")
                f.write(f"     Text: {example['text'][:100]}...\n\n")
        
        if metrics['false_negatives_examples']:
            f.write("False Negative Examples (first 10):\n")
            for i, example in enumerate(metrics['false_negatives_examples'], 1):
                f.write(f"  {i}. Time: {example['start']:.2f}-{example['end']:.2f}s\n")
                f.write(f"     Expected Line ID: {example['expected_line_id']}\n")
                f.write(f"     Expected Ang: {example['expected_ang']}\n")
                f.write(f"     Expected Source: {example['expected_source']}\n\n")
    
    logger.info(f"Generated quote report: {output_path}")
    return output_path
