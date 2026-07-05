"""
Grabbite — models package.

Re-exports every class and constant so that all existing
`from models import ...` statements continue to work unchanged.

Sub-modules (one per domain):
    constants    — shared enum tuples
    user         — User, Address
    restaurant   — Restaurant, FoodItem
    order        — Cart, Order, OrderItem, OrderStatusHistory
    payment      — Payment, WalletTransaction
    offer        — Offer, CouponUsage
    blog         — Blog
    review       — Review
    notification — Notification, AdminNotification
    support      — SupportTicket
    wishlist     — Wishlist
    admin        — AdminActivity
"""

# ── constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ROLES,
    ORDER_STATUSES,
    PAYMENT_METHODS,
    PAYMENT_STATUSES,
)

# ── user ──────────────────────────────────────────────────────────────────────
from .user import User, Address

# ── restaurant ────────────────────────────────────────────────────────────────
from .restaurant import Restaurant, FoodItem

# ── order ─────────────────────────────────────────────────────────────────────
from .order import Cart, Order, OrderItem, OrderStatusHistory

# ── payment ───────────────────────────────────────────────────────────────────
from .payment import Payment, WalletTransaction

# ── offer / coupon ────────────────────────────────────────────────────────────
from .offer import Offer, CouponUsage

# ── blog ──────────────────────────────────────────────────────────────────────
from .blog import Blog

# ── review ────────────────────────────────────────────────────────────────────
from .review import Review

# ── notification ──────────────────────────────────────────────────────────────
from .notification import Notification, AdminNotification

# ── support ───────────────────────────────────────────────────────────────────
from .support import SupportTicket

# ── wishlist ──────────────────────────────────────────────────────────────────
from .wishlist import Wishlist

# ── admin ─────────────────────────────────────────────────────────────────────
from .admin import AdminActivity

# Expose db at package level for convenience (mirrors old `from models import db`)
from db import db

__all__ = [
    # constants
    'ROLES', 'ORDER_STATUSES', 'PAYMENT_METHODS', 'PAYMENT_STATUSES',
    # user
    'User', 'Address',
    # restaurant
    'Restaurant', 'FoodItem',
    # order
    'Cart', 'Order', 'OrderItem', 'OrderStatusHistory',
    # payment
    'Payment', 'WalletTransaction',
    # offer
    'Offer', 'CouponUsage',
    # blog
    'Blog',
    # review
    'Review',
    # notification
    'Notification', 'AdminNotification',
    # support
    'SupportTicket',
    # wishlist
    'Wishlist',
    # admin
    'AdminActivity',
    # db
    'db',
]
