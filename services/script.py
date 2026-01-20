"""
Script Processing Services Module.

Combines script conversion, script locking, and drift detection services
for Gurmukhi text processing and validation.

Consolidated from:
- script_converter.py
- script_lock.py
- drift_detector.py
"""
# Re-export from original modules for backward compatibility
from services.script_converter import (
    ScriptConverter,
    ScriptDetector,
    ShahmukhiToGurmukhiConverter,
    GurmukhiToRomanTransliterator,
)
from services.script_lock import (
    ScriptLock,
    ScriptAnalysis,
    enforce_gurmukhi,
    analyze_script,
    is_gurmukhi_pure,
)
from services.drift_detector import (
    DriftDetector,
    DriftDiagnostic,
    DriftSeverity,
    DriftType,
    detect_drift,
    is_drift_acceptable,
    get_drift_metrics,
)

__all__ = [
    # Script Conversion
    'ScriptConverter',
    'ScriptDetector',
    'ShahmukhiToGurmukhiConverter',
    'GurmukhiToRomanTransliterator',
    
    # Script Lock
    'ScriptLock',
    'ScriptAnalysis',
    'enforce_gurmukhi',
    'analyze_script',
    'is_gurmukhi_pure',
    
    # Drift Detection
    'DriftDetector',
    'DriftDiagnostic',
    'DriftSeverity',
    'DriftType',
    'detect_drift',
    'is_drift_acceptable',
    'get_drift_metrics',
]

