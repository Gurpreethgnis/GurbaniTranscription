"""
Authentication routes for login, logout, and registration.
"""

import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, current_user
from auth.models import db, User, Invitation, UsageQuota, TranscriptionRecord
from auth.decorators import login_required, admin_required

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ============================================
# AUTH ROUTES
# ============================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'
        
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'error')
            return render_template('login.html')
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact an administrator.', 'error')
            return render_template('login.html')
        
        # Update last login
        user.update_last_login()
        db.session.commit()
        
        login_user(user, remember=remember)
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('index'))
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout handler."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register/<token>', methods=['GET', 'POST'])
def register(token):
    """Registration page for invited users."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    invitation = Invitation.query.filter_by(token=token).first()
    
    if invitation is None:
        flash('Invalid invitation link.', 'error')
        return redirect(url_for('auth.login'))
    
    if not invitation.is_valid:
        if invitation.is_expired:
            flash('This invitation has expired. Please request a new one.', 'error')
        else:
            flash('This invitation has already been used.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        if not name:
            errors.append('Name is required.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html', invitation=invitation)
        
        # Create user
        user = User(
            email=invitation.email,
            name=name,
            role='user',
            is_active=True
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Get user.id
        
        # Create quota for user
        quota = UsageQuota.create_for_user(
            user_id=user.id,
            limit_minutes=invitation.default_quota_minutes
        )
        db.session.add(quota)
        
        # Mark invitation as used
        invitation.mark_used(user.id)
        
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', invitation=invitation)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Update name
        if name and name != current_user.name:
            current_user.name = name
            flash('Name updated successfully.', 'success')
        
        # Update password if provided
        if new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
            elif len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                current_user.set_password(new_password)
                flash('Password updated successfully.', 'success')
        
        db.session.commit()
        return redirect(url_for('auth.profile'))
    
    # Get usage stats
    quota = current_user.quota
    recent_transcriptions = current_user.transcriptions.order_by(
        TranscriptionRecord.created_at.desc()
    ).limit(5).all()
    
    return render_template('profile.html', 
                         quota=quota,
                         recent_transcriptions=recent_transcriptions)


# ============================================
# ADMIN ROUTES
# ============================================

@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard with system overview."""
    # Get stats
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_transcriptions = TranscriptionRecord.query.count()
    pending_invitations = Invitation.query.filter(
        Invitation.used_at.is_(None),
        Invitation.expires_at > datetime.utcnow()
    ).count()
    
    # Recent transcriptions
    recent_transcriptions = TranscriptionRecord.query.order_by(
        TranscriptionRecord.created_at.desc()
    ).limit(10).all()
    
    # Users with highest usage
    top_users = db.session.query(
        User, UsageQuota
    ).join(UsageQuota).order_by(
        UsageQuota.used_minutes.desc()
    ).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         total_transcriptions=total_transcriptions,
                         pending_invitations=pending_invitations,
                         recent_transcriptions=recent_transcriptions,
                         top_users=top_users)


@admin_bp.route('/users')
@admin_required
def users():
    """User management page."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def user_detail(user_id):
    """User detail and edit page."""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update':
            user.name = request.form.get('name', user.name).strip()
            user.role = request.form.get('role', user.role)
            
            # Update quota
            if user.quota:
                new_limit = request.form.get('quota_limit', type=int)
                if new_limit is not None:
                    user.quota.monthly_limit_minutes = new_limit
            
            db.session.commit()
            flash('User updated successfully.', 'success')
        
        elif action == 'toggle_active':
            if user.id == current_user.id:
                flash('You cannot deactivate yourself.', 'error')
            else:
                user.is_active = not user.is_active
                db.session.commit()
                status = 'activated' if user.is_active else 'deactivated'
                flash(f'User {status} successfully.', 'success')
        
        elif action == 'reset_quota':
            if user.quota:
                user.quota.used_minutes = 0.0
                db.session.commit()
                flash('Quota reset successfully.', 'success')
        
        elif action == 'delete':
            if user.id == current_user.id:
                flash('You cannot delete yourself.', 'error')
            else:
                db.session.delete(user)
                db.session.commit()
                flash('User deleted successfully.', 'success')
                return redirect(url_for('admin.users'))
        
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    # Get user's transcriptions
    transcriptions = user.transcriptions.order_by(
        TranscriptionRecord.created_at.desc()
    ).limit(20).all()
    
    return render_template('admin/user_detail.html', 
                         user=user, 
                         transcriptions=transcriptions)


@admin_bp.route('/invitations')
@admin_required
def invitations():
    """Invitations management page."""
    pending = Invitation.query.filter(
        Invitation.used_at.is_(None),
        Invitation.expires_at > datetime.utcnow()
    ).order_by(Invitation.created_at.desc()).all()
    
    used = Invitation.query.filter(
        Invitation.used_at.isnot(None)
    ).order_by(Invitation.used_at.desc()).limit(20).all()
    
    expired = Invitation.query.filter(
        Invitation.used_at.is_(None),
        Invitation.expires_at <= datetime.utcnow()
    ).order_by(Invitation.expires_at.desc()).limit(20).all()
    
    return render_template('admin/invitations.html',
                         pending=pending,
                         used=used,
                         expired=expired)


@admin_bp.route('/invitations/create', methods=['POST'])
@admin_required
def create_invitation():
    """Create a new invitation."""
    email = request.form.get('email', '').lower().strip()
    quota_limit = request.form.get('quota_limit', 60, type=int)
    expires_days = request.form.get('expires_days', 7, type=int)
    
    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('admin.invitations'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('A user with this email already exists.', 'error')
        return redirect(url_for('admin.invitations'))
    
    # Check for existing pending invitation
    existing_invite = Invitation.query.filter(
        Invitation.email == email,
        Invitation.used_at.is_(None),
        Invitation.expires_at > datetime.utcnow()
    ).first()
    
    if existing_invite:
        flash('An active invitation for this email already exists.', 'warning')
        return redirect(url_for('admin.invitations'))
    
    # Create invitation
    invitation = Invitation.create_invitation(
        email=email,
        created_by=current_user.id,
        expires_days=expires_days,
        default_quota=quota_limit
    )
    db.session.add(invitation)
    db.session.commit()
    
    # Generate invite URL
    invite_url = url_for('auth.register', token=invitation.token, _external=True)
    
    flash(f'Invitation created! Share this link: {invite_url}', 'success')
    return redirect(url_for('admin.invitations'))


@admin_bp.route('/invitations/<int:invite_id>/revoke', methods=['POST'])
@admin_required
def revoke_invitation(invite_id):
    """Revoke an invitation by expiring it."""
    invitation = Invitation.query.get_or_404(invite_id)
    
    if invitation.used_at:
        flash('Cannot revoke an already used invitation.', 'error')
    else:
        invitation.expires_at = datetime.utcnow()
        db.session.commit()
        flash('Invitation revoked.', 'success')
    
    return redirect(url_for('admin.invitations'))


@admin_bp.route('/transcriptions')
@admin_required
def transcriptions():
    """All transcriptions view."""
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    records = TranscriptionRecord.query.order_by(
        TranscriptionRecord.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin/transcriptions.html', records=records)


# ============================================
# API ENDPOINTS FOR ADMIN
# ============================================

@admin_bp.route('/api/users/<int:user_id>/quota', methods=['POST'])
@admin_required
def api_update_quota(user_id):
    """API to update user quota."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if not user.quota:
        quota = UsageQuota.create_for_user(user.id, data.get('limit', 60))
        db.session.add(quota)
    else:
        if 'limit' in data:
            user.quota.monthly_limit_minutes = data['limit']
        if data.get('reset'):
            user.quota.used_minutes = 0.0
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'quota': {
            'limit': user.quota.monthly_limit_minutes,
            'used': user.quota.used_minutes,
            'remaining': user.quota.remaining_minutes
        }
    })


@admin_bp.route('/api/stats')
@admin_required
def api_stats():
    """API for admin dashboard stats."""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_transcriptions = TranscriptionRecord.query.count()
    total_minutes = db.session.query(
        db.func.sum(TranscriptionRecord.duration_seconds)
    ).scalar() or 0
    
    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'total_transcriptions': total_transcriptions,
        'total_minutes': total_minutes / 60
    })

