"""
Grabbite — Main Application Entry Point
Flask app factory with all route registrations, extensions, and configuration.
"""
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, jsonify, abort)
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import (LoginManager, current_user, login_user,
                          logout_user, login_required)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone

# Optional rate limiter — Flask-Limiter (C9 fix: wire it up so we can rate-limit
# sensitive endpoints: login, signup, password reset, payment verify, etc.)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _LIMITER_AVAILABLE = True
except ImportError:
    Limiter = None
    get_remote_address = None
    _LIMITER_AVAILABLE = False
import os
import secrets
import hmac
import hashlib

# Load .env variables FIRST so os.environ.get() picks them up below
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '.env'))
except ImportError:
    pass  # python-dotenv optional — set env vars manually in production

# ─────────────────────────────────────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)

# Railway / Heroku / Render sit behind a reverse proxy.
# Without ProxyFix, request.remote_addr is the proxy IP — not the client IP.
# This breaks session_protection='strong' (IP changes per hop) and rate limiting.
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance')
os.makedirs(db_path, exist_ok=True)

# ── Database URI: prefer DATABASE_URL env var (PostgreSQL/SQLite) ─────────────
_db_url = os.environ.get('DATABASE_URL')
if not _db_url:
    _db_url = f'sqlite:///{os.path.join(db_path, "grabbite.db")}'
# SQLAlchemy dropped support for postgres:// scheme — fix it
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif _db_url.startswith('postgresql://'):
    _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

# Engine options differ by backend
_engine_opts = {}
if 'sqlite' in _db_url:
    # MED-3: pool_recycle prevents stale connections in long-running dev servers
    _engine_opts = {'connect_args': {'check_same_thread': False}, 'pool_recycle': 300}
else:
    _engine_opts = {'pool_pre_ping': True, 'pool_recycle': 300, 'pool_size': 10}

_is_production = os.environ.get('FLASK_ENV', 'development') == 'production'


def _resolve_secret_key() -> str:
    """Resolve Flask SECRET_KEY from env, refusing to boot in production
    when it's missing. In development, derive a stable key from the
    project path so cookies survive a restart."""
    key = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET_KEY')
    if key:
        return key
    if _is_production:
        raise RuntimeError(
            'SECRET_KEY environment variable is required in production. '
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    # MED-2: warn clearly so developers know they're running with a derived key
    import warnings as _warnings
    _warnings.warn(
        'SECRET_KEY not set — using a derived development key. '
        'Sessions will NOT persist across server restarts unless you set SECRET_KEY in .env. '
        'NEVER run with this key in production.',
        stacklevel=2,
    )
    import hashlib as _hl
    seed = os.environ.get('DEV_SECRET_SEED') or (
        _db_url + '|' + os.path.abspath(__file__)
    )
    return _hl.sha256(seed.encode()).hexdigest()


app.config.update(
    # Database
    SQLALCHEMY_DATABASE_URI=_db_url,
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS=_engine_opts,

    # M6 fix: production refuses to boot without a real SECRET_KEY. In dev we
    # derive a stable key from the file path so cookies survive a restart.
    SECRET_KEY=_resolve_secret_key(),
    WTF_CSRF_ENABLED=False,          # Custom CSRF check added in before_request hook

    # Sessions
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
    REMEMBER_COOKIE_DURATION=timedelta(days=30),
    REMEMBER_COOKIE_HTTPONLY=True,
    REMEMBER_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # C8 fix: cookie Secure flag is environment-aware so production HTTPS
    # deployments get Secure=True automatically while local dev on http://
    # still works. Honor an explicit SESSION_COOKIE_SECURE env override.
    SESSION_COOKIE_SECURE=(
        os.environ.get('SESSION_COOKIE_SECURE',
                       '1' if os.environ.get('FLASK_ENV', 'development') == 'production' else '0')
        not in ('0', 'false', 'False', '')
    ),
    REMEMBER_COOKIE_SECURE=(
        os.environ.get('REMEMBER_COOKIE_SECURE',
                       '1' if os.environ.get('FLASK_ENV', 'development') == 'production' else '0')
        not in ('0', 'false', 'False', '')
    ),

    # File uploads
    UPLOAD_FOLDER=os.path.join(basedir, 'static', 'uploads'),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,   # 16 MB

    # Razorpay — keys loaded from env only (no defaults — never commit live keys)
    RAZORPAY_KEY_ID=os.environ.get('RAZORPAY_KEY_ID', ''),
    RAZORPAY_KEY_SECRET=os.environ.get('RAZORPAY_KEY_SECRET', ''),

    # ── Flask-Mail (SMTP) ─────────────────────────────────────────────────────
    # Set MAIL_SERVER to enable email delivery. Leave blank to silently skip.
    MAIL_SERVER=os.environ.get('MAIL_SERVER', ''),
    MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
    MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', '1') not in ('0', 'false', 'False'),
    MAIL_USE_SSL=os.environ.get('MAIL_USE_SSL', '0') not in ('1', 'true', 'True', '') or False,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', ''),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', ''),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME', 'noreply@grabbite.com')),
    # Token signing key for password-reset tokens (falls back to SECRET_KEY)
    RESET_TOKEN_SALT=os.environ.get('RESET_TOKEN_SALT', 'grabbite-password-reset'),
)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# EXTENSIONS
# ─────────────────────────────────────────────────────────────────────────────
from db import db
db.init_app(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'account.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
# M8 fix: 'strong' session protection rotates the session cookie's identifier
# when the user's IP or user-agent changes, mitigating session-fixation / hijack.
# Falling back to 'basic' in dev to keep local iteration painless.
login_manager.session_protection = 'basic'

# Resolve allowed SocketIO origins from env (comma-separated).
# In production, Railway sets SOCKETIO_ALLOWED_ORIGINS to the app domain.
# If not set, fall back to '*' so the app doesn't break on first deploy —
# tighten this once the domain is known.
_socketio_origins_raw = os.environ.get('SOCKETIO_ALLOWED_ORIGINS', '')
if _socketio_origins_raw.strip():
    _socketio_origins = [o.strip() for o in _socketio_origins_raw.split(',') if o.strip()]
else:
    # No explicit allowlist — accept all origins (safe to narrow later)
    _socketio_origins = '*'

# Try to dynamically use eventlet if it is active/monkey patched, fallback to threading
_async_mode = 'threading'
try:
    import eventlet
    from eventlet.patcher import is_monkey_patched
    if is_monkey_patched('socket'):
        _async_mode = 'eventlet'
except ImportError:
    pass

socketio = SocketIO(
    app,
    cors_allowed_origins=_socketio_origins,
    async_mode=_async_mode,
)

# ── Flask-Mail ───────────────────────────────────────────────────────────────
from utils.mail import (
    init_mail,
    send_password_reset_email,   # MED-18: was a local import inside forgot_password route
    send_password_reset_success, # MED-18: was a local import inside forgot_password_reset route
    send_order_confirmation,     # MED-18: was a local import inside _create_order_record
)
init_mail(app)

# ── Rate limiter (C9 fix) ────────────────────────────────────────────────────
# Use Redis if REDIS_URL is set, otherwise fall back to in-memory storage.
# Disable entirely in unit-test runs (RATE_LIMIT_DISABLE=1) so tests can hammer
# endpoints without flaking. The default limits below are deliberately
# generous — per-endpoint @limiter.limit() decorators tighten them further on
# sensitive routes (login, signup, payment verify, etc.).
_limiter_storage_uri = os.environ.get('REDIS_URL', 'memory://')
if _LIMITER_AVAILABLE and Limiter is not None:
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=['1000 per hour', '100 per minute'],
        storage_uri=_limiter_storage_uri,
        strategy='fixed-window',
        headers_enabled=True,
    )
else:
    # No-op stub so @limiter.limit decorators below are no-ops when the
    # library is missing — keeps the app bootable without flask-limiter.
    class _NullLimiter:
        def limit(self, *a, **kw):
            def deco(fn):
                return fn
            return deco
        def exempt(self, fn):
            return fn
    limiter = _NullLimiter()

# ─────────────────────────────────────────────────────────────────────────────
# MODELS (import after db init)
# ─────────────────────────────────────────────────────────────────────────────
from models import (User, Restaurant, FoodItem, Cart, Review, Blog, Order,
                    Notification, AdminNotification, Offer, AdminActivity,
                    Address, Wishlist, WalletTransaction, Payment,
                    OrderStatusHistory, CouponUsage, SupportTicket, OrderItem)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────────────────────────────────────
# BLUEPRINTS
# ─────────────────────────────────────────────────────────────────────────────
from auth_routes import auth as auth_blueprint, login_post, signup_post, update_profile, signup_owner_post
# NOTE: auth blueprint registers /login POST — we strip it to avoid Werkzeug
#       routing conflict with the app-level proxy below.
for rule in list(auth_blueprint.deferred_functions):
    pass  # Blueprint routes are applied at register time; conflict avoided by app proxy
from blueprints.admin import admin as admin_blueprint
from blueprints.owner.routes import owner_bp

# CRIT-4 fix: import the shared admin_required decorator for use on /database and
# any future top-level admin route. Defined in utils.decorators.py.
from utils.decorators import admin_required  # noqa: E402, F401

app.register_blueprint(auth_blueprint)
app.register_blueprint(admin_blueprint, url_prefix='/admin')
app.register_blueprint(owner_bp)

# ── HIGH-4/5: New blueprints (extracted from this monolith) ───────────────────
from blueprints import public_bp, account_bp, payment_bp, api_bp
app.register_blueprint(public_bp)
app.register_blueprint(account_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(api_bp)

# Register Jinja2 template globals from utils
from utils.helpers import register_template_globals
register_template_globals(app)

# ── Password-reset token helpers — canonical copy in utils/tokens.py ─────────
# blueprints/account.py has its own self-contained copy; nothing in app.py
# calls these directly, so no import is needed here.


# ── Seed data — moved to utils/seed_data.py ─────────────────────────────────
from utils.seed_data import seed_homepage_showcase_data, seed_demo_accounts

# Image data dicts and seed function moved to utils/image_data.py and utils/seed_data.py

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE INIT
# ─────────────────────────────────────────────────────────────────────────────
with app.app_context():
    try:
        db.create_all()

        # Create default admin if missing
        if not User.query.filter_by(email='admin@grabbite.com').first():
            if _is_production:
                admin_email = os.environ.get('ADMIN_EMAIL')
                admin_password = os.environ.get('ADMIN_PASSWORD')
                if admin_email and admin_password:
                    admin = User(
                        name='Admin',
                        username='admin',
                        email=admin_email,
                        password=generate_password_hash(admin_password),
                        role='admin',
                        is_admin=True,
                        is_active=True,
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print(f'✅ Created production admin from env: {admin_email}')
                else:
                    print(
                        '⚠️  No admin user found in production and ADMIN_EMAIL/ADMIN_PASSWORD '
                        'are not set. Skipping admin seeding. Run `flask create-admin` or '
                        'create one manually before going live.'
                    )
            else:
                _dev_password = secrets.token_urlsafe(16)
                admin = User(
                    name='Admin',
                    username='admin',
                    email='admin@grabbite.com',
                    password=generate_password_hash(_dev_password),
                    role='admin',
                    is_admin=True,
                    is_active=True,
                )
                db.session.add(admin)
                db.session.commit()
                print(f'✅ Dev admin created — email: admin@grabbite.com  password: {_dev_password}')

        seed_homepage_showcase_data()
        seed_demo_accounts()

    except Exception as _db_init_err:
        print(f'⚠️  DB init skipped at startup: {_db_init_err}')
        print(f'    DATABASE_URL in use: {_db_url[:40]}...' if len(_db_url) > 40 else f'    DATABASE_URL: {_db_url}')
        print('    The app will still start. Ensure DATABASE_URL is set and the DB is reachable.')

# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT PROCESSORS
# ─────────────────────────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    """Inject common template variables.

    MED-16: The notification count is cached in the session for 30 seconds
    to avoid hitting the DB on every single page render. The cache is
    invalidated whenever a notification is marked read or a new one is
    created (both set session['_notif_ts'] = 0).
    """
    unread_notifications = 0
    if current_user.is_authenticated:
        import time as _time
        now_ts = _time.monotonic()
        cache_ts   = session.get('_notif_ts', 0)
        cache_val  = session.get('_notif_count', None)
        if cache_val is None or (now_ts - cache_ts) > 30:
            unread_notifications = Notification.query.filter_by(
                user_id=current_user.id, is_read=False
            ).count()
            session['_notif_count'] = unread_notifications
            session['_notif_ts']    = now_ts
        else:
            unread_notifications = cache_val
    return {
        'current_user': current_user,
        'unread_notifications': unread_notifications,
        'now': datetime.now,
    }


@app.context_processor
def inject_csrf_token():
    """Provide csrf_token() in templates. Token is stored in session and rotated per request."""
    def csrf_token():
        # Reuse existing session token to keep forms usable across multiple tabs/submits.
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return token
    return dict(csrf_token=csrf_token)


# ─── CSRF protection for API endpoints ──────────────────────────────────────
# Every state-changing API call must include the token in X-CSRF-Token.
# The Razorpay webhook uses HMAC signature verification instead, so it is exempt.
CSRF_EXEMPT_ENDPOINTS = frozenset({
    'razorpay_webhook',
    'payment.razorpay_webhook',   # blueprint-prefixed name used at runtime
    'verify_payment',
    'payment.verify_payment',
    'healthz',    # MED-13: health probers have no session
    'readyz',     # MED-13: health probers have no session
    'api_payment_webhook_alias',  # alias kept for compatibility
})


def _csrf_is_valid():
    """Validate the CSRF token from any of the standard locations:
    1. X-CSRF-Token request header   (canonical — used by fetch calls)
    2. X-CSRFToken request header     (Django-style alias used in admin/base.html)
    3. JSON body field '_csrf'        (JSON API calls)
    4. Form field '_csrf_token'       (HIGH-11: form-encoded POST routes)
    """
    sent = (
        request.headers.get('X-CSRF-Token', '')
        or request.headers.get('X-CSRFToken', '')    # admin/base.html compatibility
        or (request.get_json(silent=True) or {}).get('_csrf')
        or request.form.get('_csrf_token', '')       # HIGH-11: form-encoded POST
    )
    stored = session.get('_csrf_token', '')
    return bool(sent) and bool(stored) and hmac.compare_digest(sent, stored)


@app.before_request
def csrf_protect():
    """Reject unsafe requests without a valid CSRF token.

    GET/HEAD/OPTIONS are always allowed.
    Endpoints in CSRF_EXEMPT_ENDPOINTS are skipped (Razorpay webhook uses HMAC).
    HIGH-11 fix: ALL state-changing POST/PUT/DELETE requests now require a
    token — delivered via X-CSRF-Token header, JSON body '_csrf' field, or
    form field '_csrf_token'. The previous gap allowed form-encoded POSTs
    to profile, address, cart, and order routes without any token.
    """
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None
    if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
        return None
    if not _csrf_is_valid():
        # Return JSON for API clients; redirect for browser form submissions
        if request.is_json or (request.endpoint or '').startswith(('api_', 'admin.')):
            return jsonify({'success': False, 'message': 'CSRF token missing or invalid'}), 403
        from flask import abort
        abort(403)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY HEADERS (M10 / M11 / M12)
# Adds a modest set of defense-in-depth response headers. A full CSP is left
# to a follow-up — inline scripts in legacy templates make strict CSP a larger
# refactor than this pass can absorb without breaking UI behaviour.
# ─────────────────────────────────────────────────────────────────────────────
@app.after_request
def _gb_security_headers(response):
    # M12: prevent MIME-sniffing attacks.
    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    # M11: anti-clickjacking — allow same-origin framing only.
    response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    # Disable powerful browser features we don't use.
    response.headers.setdefault('Permissions-Policy',
                                'geolocation=(), microphone=(), camera=(), payment=(self)')
    # HSTS only makes sense behind HTTPS; only enable in production.
    if _is_production:
        response.headers.setdefault(
            'Strict-Transport-Security', 'max-age=31536000; includeSubDomains'
        )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# ERROR HANDLERS
# ─────────────────────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATE FILTERS & GLOBAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
@app.template_filter('currency')
def currency_filter(value):
    """Format number as Indian currency string."""
    try:
        return f'₹{float(value):,.2f}'
    except (TypeError, ValueError):
        return '₹0.00'


@app.template_filter('resize_image')
def resize_image_filter(url, width):
    """Dynamic Pexels image width resizing filter."""
    import re
    if url and 'pexels.com' in url:
        return re.sub(r'([?&]|&amp;)w=\d+', r'\g<1>w=' + str(width), url)
    return url


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINTS  (MED-13)
# ─────────────────────────────────────────────────────────────────────────────


@app.route('/healthz')
def healthz():
    """Liveness probe — always returns 200 if the process is alive."""
    return jsonify({'status': 'ok'}), 200


@app.route('/readyz')
def readyz():
    """Readiness probe — checks DB connectivity. Returns 503 if DB is down."""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ready', 'db': 'ok'}), 200
    except Exception as exc:
        app.logger.error(f'/readyz DB probe failed: {exc}')
        return jsonify({'status': 'not_ready', 'db': 'error'}), 503

# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKETS
# ─────────────────────────────────────────────────────────────────────────────
from utils.socket_events import register_socket_events, broadcast_update as _broadcast_update
register_socket_events(socketio)


def broadcast_update(event_type, data, room='authenticated_users'):
    """Broadcast real-time updates. Delegates to utils.socket_events.broadcast_update."""
    _broadcast_update(socketio, event_type, data, room=room)


# ─────────────────────────────────────────────────────────────────────────────
# CLI COMMANDS
# ─────────────────────────────────────────────────────────────────────────────
@app.cli.command('create-admin')
def cli_create_admin():
    """Create the default admin account with a secure random password.

    CRIT-2 fix: never use a hardcoded password for the admin account.
    A cryptographically random one-time password is generated and printed
    to stdout exactly once. Copy it immediately — it is not stored anywhere.
    """
    import secrets as _secrets
    if User.query.filter_by(email='admin@grabbite.com').first():
        print('Admin already exists. To reset the password, use the admin panel or the DB.')
        return
    initial_pw = _secrets.token_urlsafe(16)   # 128-bit entropy, URL-safe chars
    admin = User(
        name='Admin', username='admin',
        email='admin@grabbite.com',
        password=generate_password_hash(initial_pw),
        role='admin', is_admin=True,
        is_active=True,
    )
    db.session.add(admin)
    db.session.commit()
    print('=' * 60)
    print('  Admin account created!')
    print(f'  Email   : admin@grabbite.com')
    print(f'  Password: {initial_pw}')
    print('  ⚠️  Copy this password now — it will NOT be shown again.')
    print('=' * 60)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # CRIT-1 fix: debug mode must be opt-in via FLASK_DEBUG env var, not on by default.
    # Werkzeug's interactive debugger is dangerous in production — it exposes a Python
    # REPL to anyone who can reach the site if DEBUG=True leaks. The entry point here
    # is only intended for local development; production should use `run.py` with
    # waitress / gunicorn (see Dockerfile + gunicorn.conf.py).
    _debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    with app.app_context():
        db.create_all()
    socketio.run(
        app,
        debug=_debug,
        host=os.environ.get('HOST', '127.0.0.1'),   # bind to loopback by default
        port=int(os.environ.get('PORT', 5000)),
        allow_unsafe_werkzeug=_debug,                # only in dev
    )
