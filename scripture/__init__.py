"""
Scripture services module.

Provides access to canonical scripture databases (SGGS, Dasam Granth, etc.)
for quote matching and canonical text retrieval.
"""
from scripture.scripture_service import ScriptureService
from scripture.sggs_db import SGGSDatabase
from scripture.dasam_db import DasamDatabase

__all__ = [
    'ScriptureService',
    'SGGSDatabase',
    'DasamDatabase'
]
