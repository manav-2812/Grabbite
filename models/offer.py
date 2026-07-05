"""
Grabbite — Offer (coupon) & CouponUsage models.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


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
