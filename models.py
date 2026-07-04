"""
Grabbite Database Models
Complete schema with all relationships, indexes, and constraints.
"""
from db import db
from datetime import datetime, timezone
from flask_login import UserMixin
import secrets
import string
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS / CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
ROLES = ('admin', 'customer', 'restaurant_owner', 'delivery_partner')
ORDER_STATUSES = ('cart', 'placed', 'accepted', 'preparing', 'ready',
                  'picked', 'on_the_way', 'delivered', 'cancelled', 'refunded')
PAYMENT_METHODS = ('cod', 'upi', 'card', 'wallet', 'netbanking')
PAYMENT_STATUSES = ('pending', 'paid', 'failed', 'refunded')


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


# ─────────────────────────────────────────────────────────────────────────────
# RESTAURANT
# ─────────────────────────────────────────────────────────────────────────────
class Restaurant(db.Model):
    __tablename__ = 'restaurants'

    id             = db.Column(db.Integer, primary_key=True)
    owner_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    name           = db.Column(db.String(100), nullable=False, index=True)
    location       = db.Column(db.String(200), nullable=False)
    cuisine_type   = db.Column(db.String(100), nullable=False)
    description    = db.Column(db.Text)
    phone          = db.Column(db.String(20))
    email          = db.Column(db.String(120))
    delivery_time  = db.Column(db.Integer, default=30)
    min_order      = db.Column(db.Float, default=0.0)
    delivery_fee   = db.Column(db.Float, default=40.0)
    image          = db.Column(db.String(255), default='restaurant_default.jpg')
    banner_image   = db.Column(db.String(255))
    rating         = db.Column(db.Float, default=0.0)
    total_reviews  = db.Column(db.Integer, default=0)
    tags           = db.Column(db.String(255))
    opening_time   = db.Column(db.String(10), default='09:00')
    closing_time   = db.Column(db.String(10), default='22:00')
    is_active      = db.Column(db.Boolean, default=True, index=True)
    # HIGH-9: is_approved is admin's gate (requires explicit approval);
    # is_active is operator's toggle (restaurant can self-deactivate).
    # A restaurant is visible to customers only when BOTH are True.
    # Use the is_public property or the dual filter:
    #   Restaurant.is_active==True, Restaurant.is_approved==True
    is_approved    = db.Column(db.Boolean, default=True, index=True)  # LOW-9: added index
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    food_items = db.relationship('FoodItem', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    reviews    = db.relationship('Review',   backref='restaurant', lazy=True)
    owner      = db.relationship('User',     foreign_keys=[owner_id], backref='owned_restaurants', lazy=True)

    def __init__(
        self,
        name: str = '',
        location: str = '',
        cuisine_type: str = '',
        description: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        delivery_time: int = 30,
        min_order: float = 0.0,
        delivery_fee: float = 40.0,
        image: str = 'restaurant_default.jpg',
        banner_image: Optional[str] = None,
        rating: float = 0.0,
        total_reviews: int = 0,
        tags: Optional[str] = None,
        opening_time: str = '09:00',
        closing_time: str = '22:00',
        is_active: bool = True,
        is_approved: bool = True,
        owner_id: Optional[int] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.location = location
        self.cuisine_type = cuisine_type
        self.description = description
        self.phone = phone
        self.email = email
        self.delivery_time = delivery_time
        self.min_order = min_order
        self.delivery_fee = delivery_fee
        self.image = image
        self.banner_image = banner_image
        self.rating = rating
        self.total_reviews = total_reviews
        self.tags = tags
        self.opening_time = opening_time
        self.closing_time = closing_time
        self.is_active = is_active
        self.is_approved = is_approved
        self.owner_id = owner_id

    def __repr__(self):
        return f'<Restaurant {self.name}>'

    @property
    def is_public(self) -> bool:
        """HIGH-9: True only when both is_active and is_approved are True.

        is_active  — operator toggle (restaurant can switch itself off).
        is_approved — admin gate (admin must explicitly approve new registrations).

        For SQLAlchemy queries use:
            .filter(Restaurant.is_active == True, Restaurant.is_approved == True)
        """
        return bool(self.is_active) and bool(self.is_approved)


# ─────────────────────────────────────────────────────────────────────────────
# FOOD ITEM
# ─────────────────────────────────────────────────────────────────────────────
class FoodItem(db.Model):
    __tablename__ = 'food_items'

    id               = db.Column(db.Integer, primary_key=True)
    restaurant_id    = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)
    name             = db.Column(db.String(100), nullable=False)
    price            = db.Column(db.Float, nullable=False)
    image            = db.Column(db.String(255), default='food_default.jpg')
    description      = db.Column(db.Text)
    category         = db.Column(db.String(50), default='Main Course', index=True)
    is_available     = db.Column(db.Boolean, default=True, index=True)
    is_vegetarian    = db.Column(db.Boolean, default=False)
    is_vegan         = db.Column(db.Boolean, default=False)
    is_gluten_free   = db.Column(db.Boolean, default=False)
    is_bestseller    = db.Column(db.Boolean, default=False)
    rating           = db.Column(db.Float, default=0.0)
    preparation_time = db.Column(db.Integer, default=15)
    calories         = db.Column(db.Integer)
    tags             = db.Column(db.String(255))
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    cart_items = db.relationship('Cart', backref='food_item', lazy=True, cascade='all, delete-orphan')

    def __init__(
        self,
        restaurant_id: int = 0,
        name: str = '',
        price: float = 0.0,
        description: Optional[str] = None,
        category: str = 'Main Course',
        image: str = 'food_default.jpg',
        is_available: bool = True,
        is_vegetarian: bool = False,
        is_vegan: bool = False,
        is_gluten_free: bool = False,
        is_bestseller: bool = False,
        rating: float = 0.0,
        preparation_time: int = 15,
        calories: Optional[int] = None,
        tags: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.restaurant_id = restaurant_id
        self.name = name
        self.price = price
        self.description = description
        self.category = category
        self.image = image
        self.is_available = is_available
        self.is_vegetarian = is_vegetarian
        self.is_vegan = is_vegan
        self.is_gluten_free = is_gluten_free
        self.is_bestseller = is_bestseller
        self.rating = rating
        self.preparation_time = preparation_time
        self.calories = calories
        self.tags = tags

    def __repr__(self):
        return f'<FoodItem {self.name} ₹{self.price}>'


# ─────────────────────────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────────────────────────
class Cart(db.Model):
    __tablename__ = 'cart'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=False)
    quantity     = db.Column(db.Integer, nullable=False, default=1)
    price        = db.Column(db.Float, nullable=False)
    notes        = db.Column(db.String(255))
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'food_item_id', name='uq_cart_user_food'),
        db.Index('idx_cart_user_food', 'user_id', 'food_item_id'),
    )

    def __init__(
        self,
        user_id: int = 0,
        food_item_id: int = 0,
        quantity: int = 1,
        price: float = 0.0,
        notes: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.food_item_id = food_item_id
        self.quantity = quantity
        self.price = price
        self.notes = notes

    def __repr__(self):
        return f'<Cart user={self.user_id} food={self.food_item_id} qty={self.quantity}>'


# ─────────────────────────────────────────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────────────────────────────────────────
class Order(db.Model):
    __tablename__ = 'orders'

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    restaurant_id    = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)
    order_items      = db.Column(db.JSON)
    subtotal         = db.Column(db.Float, default=0.0)
    tax              = db.Column(db.Float, default=0.0)
    delivery_fee     = db.Column(db.Float, default=40.0)
    discount         = db.Column(db.Float, default=0.0)
    total_amount     = db.Column(db.Float, nullable=False)
    delivery_address = db.Column(db.Text, nullable=False)
    delivery_phone   = db.Column(db.String(20))
    payment_method   = db.Column(db.String(50), nullable=False, default='cod')
    payment_status   = db.Column(db.String(20), default='pending', index=True)
    razorpay_order_id   = db.Column(db.String(100), index=True)   # LOW-10: added index for webhook lookup
    razorpay_payment_id = db.Column(db.String(100))
    coupon_code      = db.Column(db.String(50))
    status           = db.Column(db.String(20), default='placed', index=True)
    notes            = db.Column(db.Text)
    estimated_time   = db.Column(db.Integer)
    delivered_at     = db.Column(db.DateTime)
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    restaurant   = db.relationship('Restaurant', backref='orders', lazy=True)
    payments     = db.relationship('Payment', backref='order', lazy=True)
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy=True,
                                      order_by='OrderStatusHistory.created_at')
    # HIGH-10: normalized line items (additive — JSON column kept for backward compat)
    order_line_items = db.relationship('OrderItem', backref='order', lazy=True,
                                        cascade='all, delete-orphan')

    def __init__(
        self,
        user_id: int = 0,
        restaurant_id: int = 0,
        total_amount: float = 0.0,
        delivery_address: str = '',
        order_items: Optional[object] = None,
        subtotal: float = 0.0,
        tax: float = 0.0,
        delivery_fee: float = 40.0,
        discount: float = 0.0,
        delivery_phone: Optional[str] = None,
        payment_method: str = 'cod',
        payment_status: str = 'pending',
        status: str = 'placed',
        notes: Optional[str] = None,
        coupon_code: Optional[str] = None,
        estimated_time: Optional[int] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.restaurant_id = restaurant_id
        self.total_amount = total_amount
        self.delivery_address = delivery_address
        self.order_items = order_items
        self.subtotal = subtotal
        self.tax = tax
        self.delivery_fee = delivery_fee
        self.discount = discount
        self.delivery_phone = delivery_phone
        self.payment_method = payment_method
        self.payment_status = payment_status
        self.status = status
        self.notes = notes
        self.coupon_code = coupon_code
        self.estimated_time = estimated_time

    @property
    def items(self):
        """Return order_items for template compatibility."""
        return self.order_items if self.order_items else []

    @property
    def status_badge_class(self):
        mapping = {
            'placed': 'warning', 'accepted': 'info', 'preparing': 'primary',
            'ready': 'success', 'picked': 'success', 'on_the_way': 'success',
            'delivered': 'success', 'cancelled': 'danger', 'refunded': 'secondary'
        }
        return mapping.get(self.status, 'secondary')

    def __repr__(self):
        return f'<Order #{self.id} {self.status}>'


class OrderStatusHistory(db.Model):
    __tablename__ = 'order_status_history'

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    status     = db.Column(db.String(20), nullable=False)
    note       = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        order_id: int = 0,
        status: str = '',
        note: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.order_id = order_id
        self.status = status
        self.note = note



# ─────────────────────────────────────────────────────────────────────────────
# ORDER ITEM  (HIGH-10: normalized child table for order line items)
# ─────────────────────────────────────────────────────────────────────────────
class OrderItem(db.Model):
    """Normalized order line item.

    HIGH-10 fix: replaces the JSON blob on Order.order_items as the canonical
    line-item store. The JSON column is kept for backward compatibility.

    Migration note: new orders write to BOTH this table AND the JSON column.
    Historical orders (JSON-only) can be backfilled via the admin panel or a
    one-time script if needed.
    """
    __tablename__ = 'order_items'

    id           = db.Column(db.Integer, primary_key=True)
    order_id     = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=True)
    name         = db.Column(db.String(100), nullable=False)   # snapshot at order time
    price        = db.Column(db.Float, nullable=False)          # price at order time
    quantity     = db.Column(db.Integer, nullable=False, default=1)
    notes        = db.Column(db.String(255))
    image        = db.Column(db.String(255))                    # snapshot at order time

    food_item = db.relationship('FoodItem', backref='order_items', lazy=True)

    def __init__(
        self,
        order_id: int = 0,
        name: str = '',
        price: float = 0.0,
        quantity: int = 1,
        food_item_id: Optional[int] = None,
        notes: Optional[str] = None,
        image: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.order_id     = order_id
        self.name         = name
        self.price        = price
        self.quantity     = quantity
        self.food_item_id = food_item_id
        self.notes        = notes
        self.image        = image

    @property
    def total(self) -> float:
        """Line total: price × quantity."""
        return round(self.price * self.quantity, 2)

    def __repr__(self):
        return f'<OrderItem order={self.order_id} {self.name} x{self.quantity}>'


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT
# ─────────────────────────────────────────────────────────────────────────────
class Payment(db.Model):
    __tablename__ = 'payments'

    id                  = db.Column(db.Integer, primary_key=True)
    order_id            = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    amount              = db.Column(db.Float, nullable=False)
    currency            = db.Column(db.String(10), default='INR')
    payment_method      = db.Column(db.String(50), nullable=False, default='cod')
    # Gateway fields
    gateway             = db.Column(db.String(50), default='razorpay')
    gateway_order_id    = db.Column(db.String(200), index=True)   # razorpay order_id
    gateway_payment_id  = db.Column(db.String(200), index=True)   # razorpay payment_id
    gateway_signature   = db.Column(db.String(500))               # HMAC signature
    transaction_id      = db.Column(db.String(200))
    status              = db.Column(db.String(20), default='pending', index=True)
    gateway_response    = db.Column(db.JSON)
    # Refund
    refund_id           = db.Column(db.String(200))
    refund_status       = db.Column(db.String(20))  # requested/processing/completed/rejected
    refund_amount       = db.Column(db.Float, default=0.0)
    refunded_at         = db.Column(db.DateTime)
    remarks             = db.Column(db.Text)
    # Timestamps
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                                     onupdate=lambda: datetime.now(timezone.utc))

    # LOW-11: compound index — most lookups are (order_id, status) or (gateway_order_id, status)
    __table_args__ = (
        db.Index('ix_payments_order_status', 'order_id', 'status'),
    )

    def __init__(
        self,
        order_id: int = 0,
        user_id: Optional[int] = None,
        amount: float = 0.0,
        currency: str = 'INR',
        payment_method: str = 'cod',
        gateway: str = 'razorpay',
        gateway_order_id: Optional[str] = None,
        gateway_payment_id: Optional[str] = None,
        gateway_signature: Optional[str] = None,
        transaction_id: Optional[str] = None,
        status: str = 'pending',
        gateway_response: Optional[object] = None,
        refund_id: Optional[str] = None,
        refund_status: Optional[str] = None,
        refund_amount: float = 0.0,
        remarks: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.order_id           = order_id
        self.user_id            = user_id
        self.amount             = amount
        self.currency           = currency
        self.payment_method     = payment_method
        self.gateway            = gateway
        self.gateway_order_id   = gateway_order_id
        self.gateway_payment_id = gateway_payment_id
        self.gateway_signature  = gateway_signature
        self.transaction_id     = transaction_id
        self.status             = status
        self.gateway_response   = gateway_response
        self.refund_id          = refund_id
        self.refund_status      = refund_status
        self.refund_amount      = refund_amount
        self.remarks            = remarks

    def __repr__(self):
        return f'<Payment #{self.id} ₹{self.amount} {self.status}>'



# ─────────────────────────────────────────────────────────────────────────────
# BLOG
# ─────────────────────────────────────────────────────────────────────────────
class Blog(db.Model):
    __tablename__ = 'blogs'

    id         = db.Column(db.Integer, primary_key=True)
    title      = db.Column(db.String(200), nullable=False)
    slug       = db.Column(db.String(220), unique=True)
    content    = db.Column(db.Text, nullable=False)
    author     = db.Column(db.String(100), nullable=False, default='Grabbite Team')
    image      = db.Column(db.String(255), default='blog_default.jpg')
    excerpt    = db.Column(db.Text)
    category   = db.Column(db.String(50), default='Food')
    status     = db.Column(db.String(20), default='published', index=True)  # LOW-13 / PERF-8: index for filter_by(status=...)
    featured   = db.Column(db.Boolean, default=False)
    views      = db.Column(db.Integer, default=0)
    tags       = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        title: str = '',
        content: str = '',
        author: str = 'Grabbite Team',
        image: str = 'blog_default.jpg',
        excerpt: Optional[str] = None,
        category: str = 'Food',
        status: str = 'published',
        featured: bool = False,
        tags: Optional[str] = None,
        slug: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.content = content
        self.author = author
        self.image = image
        self.excerpt = excerpt
        self.category = category
        self.status = status
        self.featured = featured
        self.tags = tags
        self.slug = slug

    def generate_slug(self):
        """Auto-generate URL slug from title.

        LOW-8: Handles duplicate slugs — if the candidate slug already exists
        in the DB, a short random suffix is appended until the slug is unique.
        """
        import re, secrets as _sec
        base = self.title.lower()
        base = re.sub(r'[^a-z0-9\s-]', '', base)
        base = re.sub(r'\s+', '-', base.strip())
        base = base[:200]  # leave room for suffix

        candidate = base
        max_attempts = 5
        for attempt in range(max_attempts):
            # Check for conflict, but exclude self (for edit operations)
            conflict_query = Blog.query.filter(Blog.slug == candidate)
            if self.id:
                conflict_query = conflict_query.filter(Blog.id != self.id)
            if not conflict_query.first():
                self.slug = candidate
                return candidate
            suffix = _sec.token_hex(2)          # 4 hex chars — short but unique enough
            candidate = f'{base}-{suffix}'

        # Fallback: full hex to guarantee no collision
        self.slug = f'{base}-{_sec.token_hex(4)}'
        return self.slug

    def __repr__(self):
        return f'<Blog "{self.title[:40]}">'


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW
# ─────────────────────────────────────────────────────────────────────────────
class Review(db.Model):
    __tablename__ = 'reviews'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)
    order_id      = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    rating        = db.Column(db.Integer, nullable=False)
    comment       = db.Column(db.Text)
    image         = db.Column(db.String(255))
    is_approved   = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'restaurant_id', name='uq_user_restaurant_review'),
    )

    def __init__(
        self,
        user_id: int = 0,
        restaurant_id: int = 0,
        rating: int = 5,
        comment: Optional[str] = None,
        order_id: Optional[int] = None,
        image: Optional[str] = None,
        is_approved: bool = True,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.restaurant_id = restaurant_id
        self.rating = rating
        self.comment = comment
        self.order_id = order_id
        self.image = image
        self.is_approved = is_approved

    def __repr__(self):
        return f'<Review user={self.user_id} restaurant={self.restaurant_id} rating={self.rating}>'


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION
# ─────────────────────────────────────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title      = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    type       = db.Column(db.String(50))
    link       = db.Column(db.String(255))
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        user_id: int = 0,
        title: str = '',
        message: str = '',
        type: Optional[str] = None,
        link: Optional[str] = None,
        is_read: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.title = title
        self.message = message
        self.type = type
        self.link = link
        self.is_read = is_read

    def __repr__(self):
        return f'<Notification user={self.user_id} "{self.title[:30]}">'


class AdminNotification(db.Model):
    __tablename__ = 'admin_notifications'

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    message      = db.Column(db.Text, nullable=False)
    type         = db.Column(db.String(50), default='general')
    target_users = db.Column(db.String(50), default='all')
    is_sent      = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at      = db.Column(db.DateTime)

    def __init__(
        self,
        title: str = '',
        message: str = '',
        type: str = 'general',
        target_users: str = 'all',
        is_sent: bool = False,
        sent_at: Optional[datetime] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.message = message
        self.type = type
        self.target_users = target_users
        self.is_sent = is_sent
        self.sent_at = sent_at

    def __repr__(self):
        return f'<AdminNotification "{self.title[:30]}">'


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKET
# ─────────────────────────────────────────────────────────────────────────────
class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject    = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    status     = db.Column(db.String(20), default='open')
    priority   = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SupportTicket "{self.subject[:40]}" {self.status}>'


# ─────────────────────────────────────────────────────────────────────────────
# OFFER / COUPON
# ─────────────────────────────────────────────────────────────────────────────
class Offer(db.Model):
    __tablename__ = 'offers'

    id                = db.Column(db.Integer, primary_key=True)
    title             = db.Column(db.String(200), nullable=False)
    description       = db.Column(db.Text, nullable=False)
    discount_type     = db.Column(db.String(20), nullable=False)
    discount_value    = db.Column(db.Float, nullable=False)
    min_order_amount  = db.Column(db.Float, default=0)
    max_discount      = db.Column(db.Float)
    code              = db.Column(db.String(50), unique=True, index=True)
    start_date        = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_date          = db.Column(db.DateTime, nullable=False)
    is_active         = db.Column(db.Boolean, default=True)
    usage_limit       = db.Column(db.Integer)
    used_count        = db.Column(db.Integer, default=0)
    restaurant_id     = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=True)
    created_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        title: str = '',
        description: str = '',
        discount_type: str = 'percentage',
        discount_value: float = 0.0,
        end_date: Optional[datetime] = None,
        code: Optional[str] = None,
        min_order_amount: float = 0.0,
        max_discount: Optional[float] = None,
        start_date: Optional[datetime] = None,
        is_active: bool = True,
        usage_limit: Optional[int] = None,
        restaurant_id: Optional[int] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.description = description
        self.discount_type = discount_type
        self.discount_value = discount_value
        self.end_date = end_date or datetime.now(timezone.utc)
        self.code = code
        self.min_order_amount = min_order_amount
        self.max_discount = max_discount
        self.start_date = start_date or datetime.now(timezone.utc)
        self.is_active = is_active
        self.usage_limit = usage_limit
        self.restaurant_id = restaurant_id

    def is_valid(self):
        now = datetime.now(timezone.utc)
        if not self.is_active:
            return False, 'Coupon is inactive'
        if now < self.start_date:
            return False, 'Coupon is not yet active'
        if now > self.end_date:
            return False, 'Coupon has expired'
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, 'Coupon usage limit reached'
        return True, 'Valid'

    def __repr__(self):
        return f'<Offer {self.code} {self.discount_value}>'


class CouponUsage(db.Model):
    __tablename__ = 'coupon_usage'

    id         = db.Column(db.Integer, primary_key=True)
    offer_id   = db.Column(db.Integer, db.ForeignKey('offers.id'), nullable=False, index=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.id'))
    used_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('offer_id', 'user_id', name='uq_coupon_user'),
    )


# ─────────────────────────────────────────────────────────────────────────────
# WISHLIST
# ─────────────────────────────────────────────────────────────────────────────
class Wishlist(db.Model):
    __tablename__ = 'wishlist'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'restaurant_id', name='uq_wishlist'),
    )

    restaurant = db.relationship('Restaurant', backref='wishlisted_by', lazy=True)

    def __init__(
        self,
        user_id: int = 0,
        restaurant_id: int = 0,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.restaurant_id = restaurant_id

    def __repr__(self):
        return f'<Wishlist user={self.user_id} restaurant={self.restaurant_id}>'


# ─────────────────────────────────────────────────────────────────────────────
# WALLET
# ─────────────────────────────────────────────────────────────────────────────
class WalletTransaction(db.Model):
    __tablename__ = 'wallet_transactions'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount      = db.Column(db.Float, nullable=False)
    type        = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255))
    order_id    = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<WalletTransaction user={self.user_id} {self.type} ₹{self.amount}>'


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ACTIVITY LOG
# ─────────────────────────────────────────────────────────────────────────────
class AdminActivity(db.Model):
    __tablename__ = 'admin_activities'

    id          = db.Column(db.Integer, primary_key=True)
    admin_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action      = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id   = db.Column(db.Integer)
    details     = db.Column(db.Text)
    ip_address  = db.Column(db.String(45))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    admin = db.relationship('User', backref='admin_activities', lazy=True)

    def __init__(
        self,
        admin_id: int = 0,
        action: str = '',
        target_type: str = '',
        target_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.admin_id = admin_id
        self.action = action
        self.target_type = target_type
        self.target_id = target_id
        self.details = details
        self.ip_address = ip_address

    def __repr__(self):
        return f'<AdminActivity {self.action} by admin={self.admin_id}>'
