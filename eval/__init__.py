"""
Evaluation harness for transcription accuracy metrics.

This module provides tools for:
- Ground truth dataset management
- WER/CER calculation
- Quote detection accuracy metrics
"""

from eval.dataset_builder import DatasetBuilder
from eval.wer_cer_reports import calculate_wer_cer, generate_report
from eval.quote_accuracy_reports import calculate_quote_metrics, generate_quote_report

__all__ = [
    'DatasetBuilder',
    'calculate_wer_cer',
    'generate_report',
    'calculate_quote_metrics',
    'generate_quote_report'
]
