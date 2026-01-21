"""
Authentication decorators for route protection.
"""

from functools import wraps
from flask import redirect, url_for, flash, request, jsonify
from flask_login import current_user


def login_required(f):
    """
    Decorator to require login for a route.
    
    Redirects to login page if not authenticated.
    For API routes (JSON requests), returns 401.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Check if it's an API request
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.is_active:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Account is deactivated'}), 403
            flash('Your account has been deactivated. Please contact an administrator.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin role for a route.
    
    Must be used after @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        if not current_user.is_admin:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def quota_required(f):
    """
    Decorator to check if user has remaining quota.
    
    Used for transcription endpoints.
    Must be used after @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        
        # Check quota
        quota = current_user.quota
        if quota is None:
            # No quota set - allow (should not happen normally)
            return f(*args, **kwargs)
        
        quota.check_and_reset()
        
        if quota.remaining_minutes <= 0:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Monthly quota exceeded',
                    'used_minutes': quota.used_minutes,
                    'limit_minutes': quota.monthly_limit_minutes,
                    'reset_date': quota.reset_date.isoformat()
                }), 429
            flash(f'You have exceeded your monthly transcription quota of {quota.monthly_limit_minutes} minutes. '
                  f'Your quota will reset on {quota.reset_date.strftime("%B %d, %Y")}.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

