"""
Full schema sync migration — compares every model column against the live DB
and adds anything missing. Also creates any missing tables.
Run any time you update models.py.
"""
import re
import sqlite3, os

DB_PATH = os.path.join('instance', 'grabbite.db')
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# H12 fix: validate every identifier before splicing it into an SQL string.
# These helpers prevent SQL injection if a future change passes user input.
_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _safe_ident(name: str, kind: str) -> str:
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f'Unsafe {kind} identifier: {name!r}')
    return name


def cols(table):
    table = _safe_ident(table, 'table')
    cur.execute(f'PRAGMA table_info({table})')
    return {r[1] for r in cur.fetchall()}

def tables():
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {r[0] for r in cur.fetchall()}

def add(table, col, defn):
    table = _safe_ident(table, 'table')
    col   = _safe_ident(col, 'column')
    # `defn` can legitimately contain parentheses, types, defaults, etc.
    # We only allow it through if it does NOT contain any of: ; ' " -- /* */
    # which would indicate an attempt to break out of the statement.
    if any(ch in defn for ch in (';', "'", '"', '--', '/*', '*/')):
        raise ValueError(f'Unsafe column definition: {defn!r}')
    existing = cols(table)
    if col not in existing:
        try:
            cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {defn}')
            print(f'  ADDED  {table}.{col}')
        except Exception as e:
            print(f'  WARN   {table}.{col}: {e}')
    else:
        print(f'  skip   {table}.{col}')

def create_table(sql, name):
    name = _safe_ident(name, 'table')
    existing = tables()
    if name not in existing:
        cur.execute(sql)
        print(f'  CREATED table {name}')
    else:
        print(f'  skip   table {name} already exists')

# ── USERS ─────────────────────────────────────────────────────────────────────
print('\n=== users ===')
add('users', 'username',       'TEXT')
add('users', 'phone',          'TEXT')
add('users', 'contact',        'TEXT')
add('users', 'role',           "TEXT DEFAULT 'customer'")
add('users', 'wallet_balance', 'REAL DEFAULT 0.0')
add('users', 'referral_code',  'TEXT UNIQUE')
add('users', 'last_login',     'TIMESTAMP')

# ── RESTAURANTS ───────────────────────────────────────────────────────────────
print('\n=== restaurants ===')
add('restaurants', 'owner_id',      'INTEGER')
add('restaurants', 'phone',         'TEXT')
add('restaurants', 'email',         'TEXT')
add('restaurants', 'description',   'TEXT')
add('restaurants', 'banner_image',  'TEXT')
add('restaurants', 'total_reviews', 'INTEGER DEFAULT 0')
add('restaurants', 'tags',          'TEXT')
add('restaurants', 'opening_time',  "TEXT DEFAULT '09:00'")
add('restaurants', 'closing_time',  "TEXT DEFAULT '22:00'")
add('restaurants', 'is_active',     'INTEGER DEFAULT 1')
add('restaurants', 'is_approved',   'INTEGER DEFAULT 1')
add('restaurants', 'delivery_time', 'INTEGER DEFAULT 30')
add('restaurants', 'min_order',     'REAL DEFAULT 0.0')
add('restaurants', 'delivery_fee',  'REAL DEFAULT 40.0')

# ── FOOD_ITEMS ────────────────────────────────────────────────────────────────
print('\n=== food_items ===')
add('food_items', 'is_vegetarian',    'INTEGER DEFAULT 0')
add('food_items', 'is_vegan',         'INTEGER DEFAULT 0')
add('food_items', 'is_gluten_free',   'INTEGER DEFAULT 0')
add('food_items', 'is_bestseller',    'INTEGER DEFAULT 0')
add('food_items', 'rating',           'REAL DEFAULT 0.0')
add('food_items', 'preparation_time', 'INTEGER DEFAULT 15')
add('food_items', 'calories',         'INTEGER')
add('food_items', 'tags',             'TEXT')
add('food_items', 'description',      'TEXT')
add('food_items', 'category',         "TEXT DEFAULT 'Main Course'")

# ── CART ──────────────────────────────────────────────────────────────────────
print('\n=== cart ===')
add('cart', 'price', 'REAL DEFAULT 0.0')
add('cart', 'notes', 'TEXT')

# ── ORDERS ────────────────────────────────────────────────────────────────────
print('\n=== orders ===')
add('orders', 'restaurant_id',       'INTEGER')
add('orders', 'order_items',         'TEXT')  # JSON stored as text in SQLite
add('orders', 'subtotal',            'REAL DEFAULT 0.0')
add('orders', 'tax',                 'REAL DEFAULT 0.0')
add('orders', 'delivery_fee',        'REAL DEFAULT 40.0')
add('orders', 'discount',            'REAL DEFAULT 0.0')
add('orders', 'total_amount',        'REAL DEFAULT 0.0')
add('orders', 'delivery_phone',      'TEXT')
add('orders', 'payment_method',      "TEXT DEFAULT 'cod'")
add('orders', 'payment_status',      "TEXT DEFAULT 'pending'")
add('orders', 'razorpay_order_id',   'TEXT')
add('orders', 'razorpay_payment_id', 'TEXT')
add('orders', 'coupon_code',         'TEXT')
add('orders', 'status',              "TEXT DEFAULT 'placed'")
add('orders', 'notes',               'TEXT')
add('orders', 'estimated_time',      'INTEGER')
add('orders', 'delivered_at',        'TIMESTAMP')
add('orders', 'updated_at',          'TIMESTAMP')

# ── REVIEWS ───────────────────────────────────────────────────────────────────
print('\n=== reviews ===')
add('reviews', 'order_id',    'INTEGER')
add('reviews', 'image',       'TEXT')
add('reviews', 'is_approved', 'INTEGER DEFAULT 1')

# ── BLOGS ─────────────────────────────────────────────────────────────────────
print('\n=== blogs ===')
add('blogs', 'slug',       'TEXT UNIQUE')
add('blogs', 'excerpt',    'TEXT')
add('blogs', 'status',     "TEXT DEFAULT 'published'")
add('blogs', 'featured',   'INTEGER DEFAULT 0')
add('blogs', 'views',      'INTEGER DEFAULT 0')
add('blogs', 'tags',       'TEXT')
add('blogs', 'updated_at', 'TIMESTAMP')

# ── OFFERS ────────────────────────────────────────────────────────────────────
print('\n=== offers ===')
add('offers', 'code',          'TEXT UNIQUE')
add('offers', 'start_date',    'TIMESTAMP')
add('offers', 'end_date',      'TIMESTAMP')
add('offers', 'used_count',    'INTEGER DEFAULT 0')
add('offers', 'restaurant_id', 'INTEGER')
add('offers', 'max_discount',  'REAL')
add('offers', 'usage_limit',   'INTEGER')

# ── NOTIFICATIONS ─────────────────────────────────────────────────────────────
print('\n=== notifications ===')
add('notifications', 'title',    'TEXT')
add('notifications', 'type',     'TEXT')
add('notifications', 'link',     'TEXT')
add('notifications', 'is_read',  'INTEGER DEFAULT 0')

# ── ADMIN_ACTIVITIES ──────────────────────────────────────────────────────────
print('\n=== admin_activities ===')
add('admin_activities', 'ip_address',  'TEXT')
add('admin_activities', 'user_agent',  'TEXT')

# ── PAYMENTS ──────────────────────────────────────────────────────────────────
print('\n=== payments ===')
add('payments', 'user_id',            'INTEGER')
add('payments', 'currency',           "TEXT DEFAULT 'INR'")
add('payments', 'gateway',            "TEXT DEFAULT 'razorpay'")
add('payments', 'gateway_order_id',   'TEXT')
add('payments', 'gateway_payment_id', 'TEXT')
add('payments', 'gateway_signature',  'TEXT')
add('payments', 'gateway_response',   'TEXT')
add('payments', 'refund_id',          'TEXT')
add('payments', 'refund_status',      'TEXT')
add('payments', 'refund_amount',      'REAL DEFAULT 0.0')
add('payments', 'refunded_at',        'TIMESTAMP')
add('payments', 'remarks',            'TEXT')
add('payments', 'updated_at',         'TIMESTAMP')

# ── CREATE MISSING TABLES ─────────────────────────────────────────────────────
print('\n=== new tables ===')

create_table('''CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    label TEXT DEFAULT 'Home',
    full_address TEXT NOT NULL,
    city TEXT, state TEXT, pincode TEXT,
    landmark TEXT, latitude REAL, longitude REAL,
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''', 'addresses')

create_table('''CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    restaurant_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, restaurant_id)
)''', 'wishlist')

create_table('''CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''', 'order_status_history')

create_table('''CREATE TABLE IF NOT EXISTS admin_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'general',
    target_users TEXT DEFAULT 'all',
    is_sent INTEGER DEFAULT 0,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''', 'admin_notifications')

create_table('''CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT DEFAULT 'cod',
    transaction_id TEXT,
    status TEXT DEFAULT 'pending',
    gateway_response TEXT,
    refund_id TEXT,
    refunded_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''', 'payments')

create_table('''CREATE TABLE IF NOT EXISTS support_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    priority TEXT DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
)''', 'support_tickets')

create_table('''CREATE TABLE IF NOT EXISTS coupon_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    order_id INTEGER,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(offer_id, user_id)
)''', 'coupon_usage')

create_table('''CREATE TABLE IF NOT EXISTS wallet_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    order_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''', 'wallet_transactions')

conn.commit()
conn.close()
print('\nFull migration complete.')
