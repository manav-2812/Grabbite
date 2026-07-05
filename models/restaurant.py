"""
Grabbite — Restaurant & FoodItem models.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


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
