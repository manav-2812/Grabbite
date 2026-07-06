"""
Grabbite — Token Helpers
Shared password-reset token generation and verification.
Extracted from app.py (Plan 2 refactor) — canonical copy lives here.
The same logic also exists in blueprints/account.py (self-contained) for
backward compatibility; both use current_app so they read the live config.
"""
from itsdangerous import URLSafeTimedSerializer as _Serializer, SignatureExpired, BadSignature
from flask import current_app


def generate_reset_token(email: str) -> str:
    """Generate a URL-safe signed token encoding the user's email."""
    s = _Serializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt=current_app.config['RESET_TOKEN_SALT'])


def verify_reset_token(token: str, max_age_seconds: int = 1800):
    """Verify and decode a reset token. Returns email on success, None on failure."""
    s = _Serializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt=current_app.config['RESET_TOKEN_SALT'], max_age=max_age_seconds)
        return email
    except (SignatureExpired, BadSignature):
        return None
