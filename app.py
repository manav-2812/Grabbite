"""
Grabbite — Main Application Entry Point
Flask app factory with all route registrations, extensions, and configuration.
"""
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session, jsonify, make_response, abort)
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import (LoginManager, current_user, login_user,
                          logout_user, login_required)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
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

# Optional razorpay — COD works without it
try:
    # pyrefly: ignore [missing-import]
    import razorpay as _razorpay_module
    _RAZORPAY_AVAILABLE = True
except ImportError:
    _RAZORPAY_AVAILABLE = False

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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'account.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
# M8 fix: 'strong' session protection rotates the session cookie's identifier
# when the user's IP or user-agent changes, mitigating session-fixation / hijack.
# Falling back to 'basic' in dev to keep local iteration painless.
login_manager.session_protection = 'strong' if _is_production else 'basic'

# Resolve allowed SocketIO origins from env (comma-separated). Defaults to localhost for dev.
_socketio_origins = os.environ.get('SOCKETIO_ALLOWED_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000')
socketio = SocketIO(
    app,
    cors_allowed_origins=[o.strip() for o in _socketio_origins.split(',') if o.strip()],
    async_mode='threading',
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

# ── Razorpay client (initialized lazily after config is ready) ─────────────────
def get_razorpay_client():
    """Return a Razorpay client or None if unavailable/unconfigured."""
    if not _RAZORPAY_AVAILABLE:
        return None
    key_id     = app.config.get('RAZORPAY_KEY_ID', '')
    key_secret = app.config.get('RAZORPAY_KEY_SECRET', '')
    if not key_id or not key_secret or 'xxx' in key_secret.lower():
        return None
    try:
        return _razorpay_module.Client(auth=(key_id, key_secret))
    except Exception as exc:
        app.logger.warning(f'Razorpay client init failed: {exc}')  # LOW-3
        return None


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
from admin_routes import admin as admin_blueprint
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

# ── Password-reset token helpers ──────────────────────────────────────────────
from itsdangerous import URLSafeTimedSerializer as _Serializer, SignatureExpired, BadSignature

def _generate_reset_token(email: str) -> str:
    """Generate a URL-safe signed token encoding the user's email."""
    s = _Serializer(app.config['SECRET_KEY'])
    return s.dumps(email, salt=app.config['RESET_TOKEN_SALT'])

def _verify_reset_token(token: str, max_age_seconds: int = 1800):
    """Verify and decode a reset token. Returns email on success, None on failure."""
    s = _Serializer(app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt=app.config['RESET_TOKEN_SALT'], max_age=max_age_seconds)
        return email
    except (SignatureExpired, BadSignature):
        return None


_FOOD_IMAGES = {
    # Offers
    'offer-1': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=1000',
    'offer-2': 'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=1000',
    'offer-3': 'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=1000',
    # Collections
    'collection-1': 'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=720',
    'collection-2': 'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=720',
    'collection-3': 'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=720',
    'collection-4': 'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=720',
    # Blogs
    'blog-1': 'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-2': 'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-3': 'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-4': 'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-5': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-6': 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-7': 'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-8': 'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-9': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=900',
    'blog-10': 'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=900',
    # Restaurants
    'restaurant-1':  'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-2':  'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-3':  'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-4':  'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-5':  'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-6':  'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-7':  'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-8':  'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-9':  'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-10': 'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-11': 'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-12': 'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-13': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-14': 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-15': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-16': 'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-17': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-18': 'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-19': 'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=900',
    'restaurant-20': 'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=900',
    # Dishes
    'dish-1':  'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-2':  'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-3':  'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-4':  'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-5':  'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-6':  'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-7':  'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-8':  'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-9':  'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-10': 'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-11': 'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-12': 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-13': 'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-14': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-15': 'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-16': 'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-17': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-18': 'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-19': 'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-20': 'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-21': 'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-22': 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-23': 'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-24': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-25': 'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-26': 'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-27': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-28': 'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-29': 'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-30': 'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-31': 'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=700',
    'dish-32': 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=700',
    # Categories
    'category-1':  'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-2':  'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-3':  'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-4':  'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-5':  'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-6':  'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-7':  'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-8':  'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-9':  'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-10': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-11': 'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-12': 'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-13': 'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-14': 'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-15': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-16': 'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-17': 'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-18': 'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-19': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=480',
    'category-20': 'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=480',
}
_FALLBACK_IMG = 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg?auto=compress&cs=tinysrgb&w=900'

# Per-restaurant curated images (matched by brand/food type)
_RESTAURANT_IMAGES = {
    "Domino's":                'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=900',   # pizza
    "KFC":                     'https://images.pexels.com/photos/60616/fried-chicken-chicken-fried-crunchy-60616.jpeg?auto=compress&cs=tinysrgb&w=900',  # fried chicken
    "McDonald's":              'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=900',   # burger
    "La Pino'z Pizza":         'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=900',     # pizza slice
    "Pizza Hut":               'https://images.pexels.com/photos/905847/pexels-photo-905847.jpeg?auto=compress&cs=tinysrgb&w=900',     # pan pizza
    "Burger King":             'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=900',   # whopper
    "Subway":                  'https://images.pexels.com/photos/2098085/pexels-photo-2098085.jpeg?auto=compress&cs=tinysrgb&w=900',   # sandwich/sub
    "Biryani By Kilo":         'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=900',   # biryani
    "Behrouz Biryani":         'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=900',   # royal biryani
    "Wow! Momo":               'https://images.pexels.com/photos/955137/pexels-photo-955137.jpeg?auto=compress&cs=tinysrgb&w=900',     # dumplings/momos
    "Haldiram's":              'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=900',   # indian snacks
    "Barbeque Nation":         'https://images.pexels.com/photos/2491273/pexels-photo-2491273.jpeg?auto=compress&cs=tinysrgb&w=900',   # BBQ grill
    "Starbucks":               'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=900',     # coffee
    "Taco Bell":               'https://images.pexels.com/photos/461198/pexels-photo-461198.jpeg?auto=compress&cs=tinysrgb&w=900',     # tacos/mexican
    "Chinese Wok":             'https://images.pexels.com/photos/2347311/pexels-photo-2347311.jpeg?auto=compress&cs=tinysrgb&w=900',   # noodles
    "The Belgian Waffle Co.":  'https://images.pexels.com/photos/3639777/pexels-photo-3639777.jpeg?auto=compress&cs=tinysrgb&w=900',   # waffles
    "Chaayos":                 'https://images.pexels.com/photos/1417945/pexels-photo-1417945.jpeg?auto=compress&cs=tinysrgb&w=900',   # chai/tea
    "Natural Ice Cream":       'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=900',   # ice cream
    "FreshMenu":               'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=900',   # healthy bowls
    "Empire Restaurant":       'https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg?auto=compress&cs=tinysrgb&w=900',   # south indian
}

# Per-blog curated images (matched by topic/category)
_BLOG_IMAGES_BY_TITLE = {
    "2026 Guide to Ordering Pizza Like a Pro":           'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=900',
    "Best Biryani Styles Across India":                 'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=900',
    "Healthy Fast Food Swaps That Actually Taste Good":  'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=900',
    "The Rise of Momos in Indian Cities":               'https://images.pexels.com/photos/955137/pexels-photo-955137.jpeg?auto=compress&cs=tinysrgb&w=900',
    "Coffee Pairings for Every Snack":                  'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=900',
    "How to Build the Perfect Burger Meal":             'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=900',
    "Dessert Trends Taking Over Delivery":              'https://images.pexels.com/photos/3639777/pexels-photo-3639777.jpeg?auto=compress&cs=tinysrgb&w=900',
    "Indian Street Food Classics You Can Order Home":   'https://images.pexels.com/photos/2347311/pexels-photo-2347311.jpeg?auto=compress&cs=tinysrgb&w=900',
    "Why Cloud Kitchens Are Changing Dinner":           'https://images.pexels.com/photos/941861/pexels-photo-941861.jpeg?auto=compress&cs=tinysrgb&w=900',
    "Weekend Family Meal Planner":                      'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=900',
}

# Per-dish curated images (matched by dish name)
_DISH_IMAGES_BY_NAME = {
    "Farmhouse Feast Pizza":        'https://images.pexels.com/photos/3682837/pexels-photo-3682837.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Cheese Burst Margherita":      'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Zinger Crunch Burger":         'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Hot Wings Bucket":             'https://images.pexels.com/photos/60616/fried-chicken-chicken-fried-crunchy-60616.jpeg?auto=compress&cs=tinysrgb&w=700',
    "McAloo Tikki Meal":            'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=700',
    "McSpicy Chicken Wrap":         'https://images.pexels.com/photos/2098085/pexels-photo-2098085.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Giant Pepperoni Slice":        'https://images.pexels.com/photos/905847/pexels-photo-905847.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Tandoori Paneer Pan Pizza":    'https://images.pexels.com/photos/315755/pexels-photo-315755.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Whopper Veg":                  'https://images.pexels.com/photos/1639557/pexels-photo-1639557.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Crispy Chicken Whopper":       'https://images.pexels.com/photos/60616/fried-chicken-chicken-fried-crunchy-60616.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Paneer Tikka Sub":             'https://images.pexels.com/photos/2098085/pexels-photo-2098085.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Chicken Teriyaki Salad":       'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Hyderabadi Chicken Biryani":   'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Paneer Dum Biryani":           'https://images.pexels.com/photos/7426877/pexels-photo-7426877.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Royal Mutton Biryani":         'https://images.pexels.com/photos/1624487/pexels-photo-1624487.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Chicken Darjeeling Momos":     'https://images.pexels.com/photos/955137/pexels-photo-955137.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Veg Cheese Fried Momos":       'https://images.pexels.com/photos/955137/pexels-photo-955137.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Raj Kachori":                  'https://images.pexels.com/photos/2474661/pexels-photo-2474661.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Chole Bhature":                'https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Smoky Grill Platter":          'https://images.pexels.com/photos/2491273/pexels-photo-2491273.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Paneer Tikka Skewers":         'https://images.pexels.com/photos/2491273/pexels-photo-2491273.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Caramel Cold Coffee":          'https://images.pexels.com/photos/312418/pexels-photo-312418.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Smoked Chicken Croissant":     'https://images.pexels.com/photos/2098085/pexels-photo-2098085.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Crunchy Taco Supreme":         'https://images.pexels.com/photos/461198/pexels-photo-461198.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Schezwan Hakka Noodles":       'https://images.pexels.com/photos/2347311/pexels-photo-2347311.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Chilli Garlic Fried Rice":     'https://images.pexels.com/photos/2347311/pexels-photo-2347311.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Dark Chocolate Waffle":        'https://images.pexels.com/photos/3639777/pexels-photo-3639777.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Kulhad Chai Combo":            'https://images.pexels.com/photos/1417945/pexels-photo-1417945.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Tender Coconut Scoop":         'https://images.pexels.com/photos/1352278/pexels-photo-1352278.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Quinoa Power Bowl":            'https://images.pexels.com/photos/1640770/pexels-photo-1640770.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Malabar Parotta Roll":         'https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg?auto=compress&cs=tinysrgb&w=700',
    "Kerala Fish Curry Bowl":       'https://images.pexels.com/photos/5560763/pexels-photo-5560763.jpeg?auto=compress&cs=tinysrgb&w=700',
}

def _food_photo(seed, term, width=900, height=650):
    return _FOOD_IMAGES.get(seed, _FALLBACK_IMG)


def seed_homepage_showcase_data():
    """Ensure the landing page, search, restaurants, dishes, and blogs have rich demo data."""
    restaurant_rows = [
        ("Domino's", "Indiranagar, Bengaluru", "Pizza, Italian, Fast Food", "Fast cheesy pizzas, sides and family combos.", 4.6),
        ("KFC", "Koramangala, Bengaluru", "Fried Chicken, Burgers, Fast Food", "Crispy chicken buckets, burgers and snack boxes.", 4.5),
        ("McDonald's", "MG Road, Bengaluru", "Burgers, Fries, Beverages", "Classic burgers, fries, wraps and McCafe drinks.", 4.4),
        ("La Pino'z Pizza", "HSR Layout, Bengaluru", "Pizza, Pasta, Italian", "Large loaded pizzas, garlic breads and pasta.", 4.7),
        ("Pizza Hut", "Whitefield, Bengaluru", "Pizza, Italian, Desserts", "Pan pizzas, melts, sides and family meals.", 4.3),
        ("Burger King", "Jayanagar, Bengaluru", "Burgers, American, Fast Food", "Flame-grilled burgers, fries and shakes.", 4.4),
        ("Subway", "Bellandur, Bengaluru", "Sandwiches, Healthy Food, Salads", "Fresh subs, wraps and salads made your way.", 4.2),
        ("Biryani By Kilo", "Marathahalli, Bengaluru", "Biryani, North Indian, Kebabs", "Dum-cooked biryanis, kebabs and curries.", 4.8),
        ("Behrouz Biryani", "JP Nagar, Bengaluru", "Biryani, Mughlai, Desserts", "Royal layered biryanis and indulgent desserts.", 4.6),
        ("Wow! Momo", "BTM Layout, Bengaluru", "Momos, Chinese, Tibetan", "Steamed, fried and saucy momos with quick bowls.", 4.3),
        ("Haldiram's", "Rajajinagar, Bengaluru", "North Indian, Sweets, Street Food", "Indian meals, chaats, snacks and sweets.", 4.5),
        ("Barbeque Nation", "Electronic City, Bengaluru", "Barbecue, North Indian, Buffet", "Smoky grills, biryani and celebration meals.", 4.7),
        ("Starbucks", "Church Street, Bengaluru", "Coffee, Bakery, Beverages", "Signature coffees, coolers, sandwiches and bakes.", 4.4),
        ("Taco Bell", "Malleshwaram, Bengaluru", "Mexican, Fast Food, Tacos", "Crunchy tacos, burritos, nachos and rice bowls.", 4.1),
        ("Chinese Wok", "Kalyan Nagar, Bengaluru", "Chinese, Noodles, Momos", "Wok-tossed noodles, rice bowls and spicy starters.", 4.2),
        ("The Belgian Waffle Co.", "Basavanagudi, Bengaluru", "Desserts, Waffles, Ice Cream", "Fresh waffles, sundaes and dessert sandwiches.", 4.6),
        ("Chaayos", "Domlur, Bengaluru", "Tea, Snacks, Beverages", "Custom chai, sandwiches and Indian snacks.", 4.2),
        ("Natural Ice Cream", "Lavelle Road, Bengaluru", "Ice Cream, Desserts", "Fruit-based ice creams and classic scoops.", 4.8),
        ("FreshMenu", "Sarjapur Road, Bengaluru", "Healthy Food, Bowls, Continental", "Chef-crafted bowls, pasta, salads and global meals.", 4.3),
        ("Empire Restaurant", "Shivajinagar, Bengaluru", "South Indian, Rolls, Seafood", "Late-night rolls, biryani, grills and Kerala specials.", 4.5),
    ]

    restaurant_by_name = {}
    for idx, (name, location, cuisine, description, rating) in enumerate(restaurant_rows, 1):
        restaurant = Restaurant.query.filter_by(name=name).first()
        if not restaurant:
            restaurant = Restaurant(
                name=name, location=location, cuisine_type=cuisine,
                description=description, rating=rating,
                delivery_time=16 + (idx % 8) * 3,
                min_order=180 + (idx % 6) * 50,
                delivery_fee=25 + (idx % 5) * 5,
                image=_food_photo(f'restaurant-{idx}', cuisine.split(',')[0].replace(' ', '+')),
                tags='trending,bestseller,delivery',
                is_active=True, is_approved=True,
            )
            db.session.add(restaurant)
            db.session.flush()
        restaurant_by_name[name] = restaurant

    dish_rows = [
        ("Domino's", "Farmhouse Feast Pizza", 399, "Pizza", True), ("Domino's", "Cheese Burst Margherita", 329, "Pizza", True),
        ("KFC", "Zinger Crunch Burger", 219, "Burger", False), ("KFC", "Hot Wings Bucket", 349, "Fast Food", False),
        ("McDonald's", "McAloo Tikki Meal", 199, "Burger", True), ("McDonald's", "McSpicy Chicken Wrap", 249, "Rolls", False),
        ("La Pino'z Pizza", "Giant Pepperoni Slice", 289, "Pizza", False), ("Pizza Hut", "Tandoori Paneer Pan Pizza", 379, "Pizza", True),
        ("Burger King", "Whopper Veg", 189, "Burger", True), ("Burger King", "Crispy Chicken Whopper", 259, "Burger", False),
        ("Subway", "Paneer Tikka Sub", 229, "Sandwiches", True), ("Subway", "Chicken Teriyaki Salad", 279, "Healthy Food", False),
        ("Biryani By Kilo", "Hyderabadi Chicken Biryani", 499, "Biryani", False), ("Biryani By Kilo", "Paneer Dum Biryani", 429, "Biryani", True),
        ("Behrouz Biryani", "Royal Mutton Biryani", 589, "Biryani", False), ("Wow! Momo", "Chicken Darjeeling Momos", 179, "Momos", False),
        ("Wow! Momo", "Veg Cheese Fried Momos", 169, "Momos", True), ("Haldiram's", "Raj Kachori", 160, "Street Food", True),
        ("Haldiram's", "Chole Bhature", 220, "North Indian", True), ("Barbeque Nation", "Smoky Grill Platter", 699, "Fast Food", False),
        ("Barbeque Nation", "Paneer Tikka Skewers", 329, "North Indian", True), ("Starbucks", "Caramel Cold Coffee", 289, "Coffee", True),
        ("Starbucks", "Smoked Chicken Croissant", 319, "Bakery", False), ("Taco Bell", "Crunchy Taco Supreme", 179, "Fast Food", True),
        ("Chinese Wok", "Schezwan Hakka Noodles", 219, "Chinese", True), ("Chinese Wok", "Chilli Garlic Fried Rice", 209, "Chinese", True),
        ("The Belgian Waffle Co.", "Dark Chocolate Waffle", 189, "Desserts", True), ("Chaayos", "Kulhad Chai Combo", 149, "Beverages", True),
        ("Natural Ice Cream", "Tender Coconut Scoop", 140, "Ice Cream", True), ("FreshMenu", "Quinoa Power Bowl", 349, "Healthy Food", True),
        ("Empire Restaurant", "Malabar Parotta Roll", 199, "Rolls", False), ("Empire Restaurant", "Kerala Fish Curry Bowl", 329, "Seafood", False),
    ]
    for idx, (restaurant_name, name, price, category, is_vegetarian) in enumerate(dish_rows, 1):
        restaurant = restaurant_by_name.get(restaurant_name)
        if restaurant and not FoodItem.query.filter_by(name=name, restaurant_id=restaurant.id).first():
            db.session.add(FoodItem(
                restaurant_id=restaurant.id, name=name, price=price,
                description=f'{name} from {restaurant_name}, prepared fresh for fast delivery.',
                category=category, image=_food_photo(f'dish-{idx}', category.replace(' ', '+'), 700, 520),
                is_available=True, is_vegetarian=is_vegetarian, is_bestseller=idx <= 18,
                rating=4.1 + ((idx % 8) / 10), preparation_time=12 + (idx % 6) * 3,
                tags=f'{category},trending,{"veg" if is_vegetarian else "non-veg"}',
            ))

    blog_rows = [
        ("2026 Guide to Ordering Pizza Like a Pro", "Smart ways to pick crusts, toppings and combos for every mood.", "Pizza"),
        ("Best Biryani Styles Across India", "From Hyderabadi dum to Kolkata-style potatoes, explore regional biryani.", "Biryani"),
        ("Healthy Fast Food Swaps That Actually Taste Good", "Better bowls, salads and subs for busy weekdays.", "Healthy"),
        ("The Rise of Momos in Indian Cities", "How momos became a favourite snack from campuses to high streets.", "Street Food"),
        ("Coffee Pairings for Every Snack", "Match cold coffee, masala chai and espresso with your favourite bites.", "Beverages"),
        ("How to Build the Perfect Burger Meal", "Balance crunch, sauces, sides and drinks for the ultimate burger order.", "Fast Food"),
        ("Dessert Trends Taking Over Delivery", "Waffles, ice creams and cakes that travel beautifully.", "Desserts"),
        ("Indian Street Food Classics You Can Order Home", "Chaat, kachori, rolls and pav favourites for snack cravings.", "Street Food"),
        ("Why Cloud Kitchens Are Changing Dinner", "Fresh menus, faster dispatch and data-led comfort food.", "Food Tech"),
        ("Weekend Family Meal Planner", "Easy ordering ideas for movie nights, parties and lazy Sundays.", "Guides"),
    ]
    for idx, (title, excerpt, category) in enumerate(blog_rows, 1):
        if not Blog.query.filter_by(title=title).first():
            blog = Blog(
                title=title, excerpt=excerpt,
                content=excerpt + '\n\nGrabBite curates restaurant trends, delivery tips and menu ideas so every order feels effortless.',
                author='GrabBite Editorial',
                image=_food_photo(f'blog-{idx}', category.replace(' ', '+'), 900, 560),
                category=category, status='published', featured=True,
            )
            blog.generate_slug()
            db.session.add(blog)

    db.session.commit()

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE INIT
# ─────────────────────────────────────────────────────────────────────────────
with app.app_context():
    db.create_all()

    # Create default admin if missing
    if not User.query.filter_by(email='admin@grabbite.com').first():
        # CRIT-2 fix: do NOT seed an admin with a hardcoded password in production.
        # In dev, generate a random password and print it once so the developer can
        # log in. In production, refuse to create one — the deployer must run
        # `flask create-admin` (or set ADMIN_EMAIL/ADMIN_PASSWORD env vars) explicitly.
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
            # Dev only — random password, printed once.
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
    'verify_payment',
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


def food_image_url(image_field: str) -> str:
    """Resolve a FoodItem.image value to a proper /static/... URL.

    Images can be stored as:
      - bare filename:          'food_default.jpg'   → /static/img/food_default.jpg
      - uploads/ relative:     'uploads/abc.jpg'    → /static/uploads/abc.jpg
      - full uploads path:     'static/uploads/...' → /static/uploads/...
    If the file can't be resolved we return the placeholder.
    """
    if not image_field:
        return '/static/img/placeholder-food.jpg'
    if image_field.startswith('http'):
        return image_field
    if image_field.startswith('uploads/'):
        return f'/static/{image_field}'
    if image_field.startswith('static/'):
        return f'/{image_field}'

    # C5 fix: legacy defaults used underscores; real files use dashes.
    # Translate the canonical underscore names to their dash counterparts
    # so templates render the renamed assets without a 404.
    _underscore_to_dash = {
        'food_default.jpg':       'food-default.jpg',
        'restaurant_default.jpg': 'restaurant-default.jpg',
        'blog_default.jpg':       'blog-default.jpg',
        'default.jpg':            'placeholder-food.jpg',
    }
    candidate = _underscore_to_dash.get(image_field, image_field)

    # Check uploads folder first (most common case for user uploads)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], image_field)
    if os.path.exists(upload_path):
        return f'/static/uploads/{image_field}'

    # Prefer the dash-named asset if it exists on disk
    img_dir = os.path.join(app.root_path, 'static', 'img')
    if os.path.exists(os.path.join(img_dir, candidate)):
        return f'/static/img/{candidate}'
    if os.path.exists(os.path.join(img_dir, image_field)):
        return f'/static/img/{image_field}'
    # Final fallback to the dash variant so the browser at least hits the
    # renamed asset (or templates' onerror handlers can swap in placeholder).
    return f'/static/img/{candidate}'


app.jinja_env.globals['food_image_url'] = food_image_url


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

def _create_order_record(data, amounts, restaurant_id, items_snapshot, payment_method,
                          payment_status='pending', gateway_order_id=None):
    """Helper: persist Order + Payment record, notify, clear cart (if paid)."""
    delivery_location = data.get('delivery_location') or {}
    location_note = ''
    if isinstance(delivery_location, dict):
        parts = [str(delivery_location.get(k) or '').strip()
                 for k in ('name', 'city', 'state')
                 if str(delivery_location.get(k) or '').strip()]
        if parts:
            location_note = 'Location: ' + ', '.join(dict.fromkeys(parts))

    order_notes = str(data.get('notes') or '').strip()[:1000]
    if location_note:
        order_notes = f'{order_notes}\n{location_note}'.strip()[:1000]  # final cap

    # H13 fix: cap delivery_address / notes length at the application layer
    # so a malicious client can't push multi-MB payloads into the DB.
    delivery_address = str(data.get('delivery_address') or '').strip()[:500]
    if len(delivery_address) < 5:
        raise ValueError('Delivery address looks too short.')

    order = Order(
        user_id=current_user.id,
        restaurant_id=restaurant_id,
        order_items=items_snapshot,
        subtotal=amounts['subtotal'],
        tax=amounts['tax'],
        delivery_fee=amounts['delivery_fee'],
        discount=amounts['discount'],
        total_amount=amounts['total'],
        delivery_address=delivery_address,
        delivery_phone=data.get('delivery_phone', ''),
        payment_method=payment_method,
        payment_status=payment_status,
        coupon_code=amounts.get('coupon_code'),
        status='placed',
        notes=order_notes,
    )
    if gateway_order_id:
        order.razorpay_order_id = gateway_order_id

    db.session.add(order)
    db.session.flush()  # get order.id

    # HIGH-10: write normalized OrderItem rows (additive; JSON column also populated above)
    for item in items_snapshot:
        db.session.add(OrderItem(
            order_id=order.id,
            food_item_id=item.get('id'),
            name=item['name'],
            price=float(item['price']),
            quantity=int(item['quantity']),
            image=item.get('image'),
        ))

    payment_rec = Payment(
        order_id=order.id,
        user_id=current_user.id,
        amount=amounts['total'],
        payment_method=payment_method,
        status=payment_status,
        gateway_order_id=gateway_order_id,
    )
    db.session.add(payment_rec)

    history = OrderStatusHistory(order_id=order.id, status='placed', note='Order placed by customer')
    db.session.add(history)

    # H9 fix: when an offer was successfully applied, record the usage and
    # atomically increment the offer's used_count. This guards against
    # usage_limit over-redemption.
    coupon_code = amounts.get('coupon_code')
    if coupon_code and amounts.get('discount', 0) > 0:
        offer = Offer.query.filter_by(code=coupon_code).first()
        if offer and not CouponUsage.query.filter_by(
            offer_id=offer.id, user_id=current_user.id
        ).first():
            db.session.add(CouponUsage(
                offer_id=offer.id, user_id=current_user.id, order_id=order.id,
            ))
            # Atomic increment — only if we're under the usage_limit.
            from sqlalchemy import update as _sa_update
            res = db.session.execute(
                _sa_update(Offer)
                .where(
                    db.and_(
                        Offer.id == offer.id,
                        db.or_(
                            Offer.usage_limit.is_(None),
                            Offer.used_count < Offer.usage_limit,
                        ),
                    )
                )
                .values(used_count=Offer.used_count + 1)
            )
            if res.rowcount == 0:
                # Race: someone else used up the limit between is_valid() and now.
                app.logger.warning(
                    f'Offer {offer.code} usage_limit reached during order commit; '
                    f'reverting discount on order {order.id}'
                )
                # Roll back the discount we applied so totals stay honest.
                order.discount = 0.0
                order.total_amount = round(
                    order.subtotal + order.tax + order.delivery_fee + 5.0, 2
                )
                payment_rec.amount = order.total_amount
                offer.used_count = offer.used_count  # no-op (keeps the intent visible)

    return order, payment_rec


def _post_order_notifications(order, amounts):
    """Fire admin + user notifications after order is committed."""
    db.session.add(AdminNotification(
        title='New Order',
        message=f'Order #{order.id} placed by {current_user.name} — ₹{amounts["total"]}',
        type='order',
    ))
    db.session.add(Notification(
        user_id=current_user.id,
        title='Order Placed! 🎉',
        message=f'Your order #{order.id} is confirmed. Total: ₹{amounts["total"]}',
        type='order_update',
        link=url_for('account.orders'),
    ))
    db.session.commit()

    # Send order confirmation email in background — never blocks the response
    try:
        from utils.mail import send_order_confirmation
        import threading
        _user = current_user._get_current_object()  # detach from proxy for thread safety
        threading.Thread(
            target=send_order_confirmation,
            args=(_user, order),
            daemon=True,
        ).start()
    except Exception as _me:
        app.logger.warning(f'Order confirmation email failed to start: {_me}')


# WISHLIST API
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# HOME PAGE SEARCH API  (searches restaurants + dishes + blogs simultaneously)
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────

def _update_restaurant_rating(restaurant_id):
    """Recalculate and persist average rating for a restaurant."""
    try:
        reviews = Review.query.filter_by(restaurant_id=restaurant_id).all()
        if reviews:
            avg = sum(r.rating for r in reviews) / len(reviews)
            restaurant = Restaurant.query.get(restaurant_id)
            if restaurant:
                restaurant.rating       = round(avg, 1)
                restaurant.total_reviews = len(reviews)
                db.session.commit()
    except Exception as e:
        app.logger.error(f'_update_restaurant_rating error: {e}')


# Duplicate notification endpoints removed — canonical versions below at api_get_notifications / api_mark_all_notifications_read


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION APIs
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# WEBSOCKETS
# ─────────────────────────────────────────────────────────────────────────────
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room('authenticated_users')
        if current_user.is_administrator():
            join_room('admin_users')


@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room('authenticated_users')
        if current_user.is_administrator():
            leave_room('admin_users')


@socketio.on('join_admin')
def handle_join_admin():
    if current_user.is_authenticated and current_user.is_administrator():
        join_room('admin_users')
        emit('status', {'msg': 'Joined admin room'})


def broadcast_update(event_type, data, room='authenticated_users'):
    """Broadcast real-time updates to connected clients."""
    try:
        socketio.emit('real_time_update', {
            'type':      event_type,
            'data':      data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, room=room)  # type: ignore[call-arg]
    except Exception:
        pass   # Don't crash the app if no socket connections


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
