"""
Grabbite — User & Address models.
"""
from db import db
from datetime import datetime, timezone
from flask_login import UserMixin
import secrets
import string
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# USER
# ─────────────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    # HIGH-8 fix: username and contact are legacy aliases.
    # The DB columns are kept for gradual deprecation (no risky DROP COLUMN);
    # use the @property accessors below for all read/write access.
    _username       = db.Column('username', db.String(100))
    email           = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password        = db.Column(db.String(255), nullable=False)
    phone           = db.Column(db.String(20))
    _contact        = db.Column('contact', db.String(20))
    profile_photo   = db.Column(db.String(255), default='default.jpg')
    address         = db.Column(db.Text)
    role            = db.Column(db.String(30), default='customer')
    is_admin        = db.Column(db.Boolean, default=False)
    is_active       = db.Column(db.Boolean, default=True)
    wallet_balance  = db.Column(db.Float, default=0.0)
    referral_code   = db.Column(db.String(20), unique=True, index=True)  # LOW-12: explicit index; unique alone not guaranteed in SQLite
    last_login      = db.Column(db.DateTime)
    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    cart_items       = db.relationship('Cart',             backref='user', lazy=True, cascade='all, delete-orphan')
    orders           = db.relationship('Order',            backref='user', lazy=True)
    reviews          = db.relationship('Review',           backref='user', lazy=True)
    notifications    = db.relationship('Notification',     backref='user', lazy=True, cascade='all, delete-orphan')
    support_tickets  = db.relationship('SupportTicket',    backref='user', lazy=True)
    addresses        = db.relationship('Address',          backref='user', lazy=True, cascade='all, delete-orphan')
    wishlist_items   = db.relationship('Wishlist',         backref='user', lazy=True, cascade='all, delete-orphan')
    wallet_txns      = db.relationship('WalletTransaction',backref='user', lazy=True)

    def __init__(
        self,
        name: str = '',
        email: str = '',
        password: str = '',
        username: Optional[str] = None,   # HIGH-8: accepted but routes to name
        phone: Optional[str] = None,
        contact: Optional[str] = None,    # HIGH-8: accepted but routes to phone
        profile_photo: str = 'default.jpg',
        address: Optional[str] = None,
        role: str = 'customer',
        is_admin: bool = False,
        is_active: bool = True,
        wallet_balance: float = 0.0,
        referral_code: Optional[str] = None,
        last_login: Optional[datetime] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.email = email
        self.password = password
        # HIGH-8: username kwarg sets name if no explicit name provided
        if username is not None and not name:
            self.name = username
        self.phone = phone or contact  # canonical field
        self.profile_photo = profile_photo
        self.address = address
        self.role = role
        self.is_admin = is_admin
        self.is_active = is_active
        self.wallet_balance = wallet_balance
        self.referral_code = referral_code
        self.last_login = last_login

    # ── HIGH-8: Computed property accessors for legacy fields ─────────────────
    @property
    def username(self) -> str:
        """Legacy alias for name, as a URL-safe slug. Read-only from DB perspective."""
        return self.name.lower().replace(' ', '_') if self.name else ''

    @username.setter
    def username(self, value: Optional[str]) -> None:
        """Setting username is a no-op (name is the canonical field)."""
        # Intentionally ignored — keeps call sites that do user.username = ... working
        pass

    @property
    def contact(self) -> Optional[str]:
        """Legacy alias for phone."""
        return self.phone

    @contact.setter
    def contact(self, value: Optional[str]) -> None:
        """Setting contact writes through to phone (the canonical field)."""
        if value:
            self.phone = value

    def is_administrator(self):
        return self.is_admin or self.role == 'admin'

    def is_restaurant_owner(self):
        return self.role == 'restaurant_owner'

    def is_delivery_partner(self):
        return self.role == 'delivery_partner'

    def generate_referral_code(self):
        chars = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(chars) for _ in range(8))
        self.referral_code = code
        return code

    def __repr__(self):
        return f'<User {self.email}>'


# ─────────────────────────────────────────────────────────────────────────────
# ADDRESS
# ─────────────────────────────────────────────────────────────────────────────
class Address(db.Model):
    __tablename__ = 'addresses'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    label        = db.Column(db.String(50), default='Home')
    full_address = db.Column(db.Text, nullable=False)
    city         = db.Column(db.String(100))
    state        = db.Column(db.String(100))
    pincode      = db.Column(db.String(10))
    landmark     = db.Column(db.String(200))
    latitude     = db.Column(db.Float)
    longitude    = db.Column(db.Float)
    is_default   = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        user_id: int = 0,
        full_address: str = '',
        label: str = 'Home',
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None,
        landmark: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        is_default: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.full_address = full_address
        self.label = label
        self.city = city
        self.state = state
        self.pincode = pincode
        self.landmark = landmark
        self.latitude = latitude
        self.longitude = longitude
        self.is_default = is_default

    def __repr__(self):
        return f'<Address {self.label}: {self.full_address[:40]}>'
