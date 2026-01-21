"""
Authentication module for Shabad Guru.

Provides invite-only user authentication, admin management,
usage quotas, and per-user transcription history.
"""

from auth.models import db, User, Invitation, UsageQuota, TranscriptionRecord
from auth.routes import auth_bp, admin_bp
from auth.decorators import login_required, admin_required

__all__ = [
    'db',
    'User',
    'Invitation', 
    'UsageQuota',
    'TranscriptionRecord',
    'auth_bp',
    'admin_bp',
    'login_required',
    'admin_required',
]

