"""
Grabbite — Cart, Order, OrderItem, and OrderStatusHistory models.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


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
    payments     = db.relationship('Payment', backref='order', lazy=True,
                                    cascade='all, delete-orphan')
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy=True,
                                      order_by='OrderStatusHistory.created_at',
                                      cascade='all, delete-orphan')
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
