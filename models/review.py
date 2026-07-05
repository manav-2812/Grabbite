"""
Grabbite — Review model.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


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
