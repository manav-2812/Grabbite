"""
Grabbite Utility Decorators
Role-based access control decorators used across all Blueprints.

HIGH-6 fix: admin_required was previously reimplemented in admin_routes.py.
That duplicate has been removed — this file is now the single source of truth.
Import from here in every Blueprint:
    from utils.decorators import admin_required, owner_required
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """Require the logged-in user to be an admin. Returns 403 for API routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_administrator():
            abort(403)
        return f(*args, **kwargs)
    return decorated


def owner_required(f):
    """Require the logged-in user to be a restaurant owner or admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not (current_user.is_restaurant_owner() or current_user.is_administrator()):
            flash('Restaurant owner access required.', 'error')
            abort(403)
        return f(*args, **kwargs)
    return decorated
