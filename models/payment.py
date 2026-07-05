"""
Grabbite — Payment & WalletTransaction models.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


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
# WALLET TRANSACTION
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
