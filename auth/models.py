"""
Database models for authentication and user management.

Models:
- User: User accounts with roles
- Invitation: Invite tokens for new user registration
- UsageQuota: Monthly transcription limits per user
- TranscriptionRecord: Per-user transcription history
"""

import secrets
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    quota = db.relationship('UsageQuota', backref='user', uselist=False, lazy=True,
                           cascade='all, delete-orphan')
    transcriptions = db.relationship('TranscriptionRecord', backref='user', lazy='dynamic',
                                    cascade='all, delete-orphan')
    invitations_sent = db.relationship('Invitation', backref='creator', lazy='dynamic',
                                       foreign_keys='Invitation.created_by')
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify the password against the hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == 'admin'
    
    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f'<User {self.email}>'


class Invitation(db.Model):
    """Invitation tokens for new user registration."""
    
    __tablename__ = 'invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Default quota for invited user (in minutes)
    default_quota_minutes = db.Column(db.Integer, default=60, nullable=False)
    
    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def create_invitation(cls, email: str, created_by: int, 
                         expires_days: int = 7,
                         default_quota: int = 60) -> 'Invitation':
        """Create a new invitation."""
        return cls(
            email=email.lower().strip(),
            token=cls.generate_token(),
            created_by=created_by,
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
            default_quota_minutes=default_quota
        )
    
    @property
    def is_valid(self) -> bool:
        """Check if invitation is still valid (not used and not expired)."""
        return self.used_at is None and datetime.utcnow() < self.expires_at
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.utcnow() >= self.expires_at
    
    def mark_used(self, user_id: int) -> None:
        """Mark invitation as used."""
        self.used_at = datetime.utcnow()
        self.used_by = user_id
    
    def __repr__(self) -> str:
        return f'<Invitation {self.email} valid={self.is_valid}>'


class UsageQuota(db.Model):
    """Usage quota tracking per user."""
    
    __tablename__ = 'usage_quotas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    monthly_limit_minutes = db.Column(db.Integer, default=60, nullable=False)
    used_minutes = db.Column(db.Float, default=0.0, nullable=False)
    reset_date = db.Column(db.DateTime, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    @classmethod
    def create_for_user(cls, user_id: int, limit_minutes: int = 60) -> 'UsageQuota':
        """Create quota for a new user."""
        # Reset date is first day of next month
        now = datetime.utcnow()
        if now.month == 12:
            reset_date = datetime(now.year + 1, 1, 1)
        else:
            reset_date = datetime(now.year, now.month + 1, 1)
        
        return cls(
            user_id=user_id,
            monthly_limit_minutes=limit_minutes,
            used_minutes=0.0,
            reset_date=reset_date
        )
    
    def check_and_reset(self) -> None:
        """Check if quota should be reset and reset if needed."""
        now = datetime.utcnow()
        if now >= self.reset_date:
            self.used_minutes = 0.0
            # Set next reset date
            if now.month == 12:
                self.reset_date = datetime(now.year + 1, 1, 1)
            else:
                self.reset_date = datetime(now.year, now.month + 1, 1)
            self.last_updated = now
    
    @property
    def remaining_minutes(self) -> float:
        """Get remaining minutes in quota."""
        self.check_and_reset()
        return max(0, self.monthly_limit_minutes - self.used_minutes)
    
    @property
    def usage_percentage(self) -> float:
        """Get usage as percentage (0-100)."""
        if self.monthly_limit_minutes == 0:
            return 100.0
        return min(100.0, (self.used_minutes / self.monthly_limit_minutes) * 100)
    
    def can_transcribe(self, duration_minutes: float) -> bool:
        """Check if user can transcribe given duration."""
        self.check_and_reset()
        return self.remaining_minutes >= duration_minutes
    
    def add_usage(self, duration_minutes: float) -> None:
        """Add usage to quota."""
        self.check_and_reset()
        self.used_minutes += duration_minutes
        self.last_updated = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f'<UsageQuota user_id={self.user_id} {self.used_minutes}/{self.monthly_limit_minutes}>'


class TranscriptionRecord(db.Model):
    """Record of transcriptions per user."""
    
    __tablename__ = 'transcription_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    filename = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(500), nullable=False)
    duration_seconds = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='pending', nullable=False)
    # Status: pending, processing, completed, failed
    
    # Output file paths (relative to outputs directory)
    output_txt = db.Column(db.String(500), nullable=True)
    output_json = db.Column(db.String(500), nullable=True)
    
    # Processing metadata
    error_message = db.Column(db.Text, nullable=True)
    segments_count = db.Column(db.Integer, nullable=True)
    quotes_detected = db.Column(db.Integer, nullable=True)
    
    @property
    def duration_minutes(self) -> float:
        """Get duration in minutes."""
        return self.duration_seconds / 60.0
    
    @property
    def is_completed(self) -> bool:
        """Check if transcription completed successfully."""
        return self.status == 'completed'
    
    def mark_processing(self) -> None:
        """Mark as processing."""
        self.status = 'processing'
    
    def mark_completed(self, output_txt: str = None, output_json: str = None,
                      segments_count: int = None, quotes_detected: int = None) -> None:
        """Mark as completed with output info."""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        if output_txt:
            self.output_txt = output_txt
        if output_json:
            self.output_json = output_json
        if segments_count is not None:
            self.segments_count = segments_count
        if quotes_detected is not None:
            self.quotes_detected = quotes_detected
    
    def mark_failed(self, error_message: str) -> None:
        """Mark as failed with error message."""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
    
    def __repr__(self) -> str:
        return f'<TranscriptionRecord {self.original_filename} status={self.status}>'

