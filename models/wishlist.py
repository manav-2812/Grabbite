"""
Grabbite — Wishlist model.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


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
