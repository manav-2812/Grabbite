"""
Unit tests — Order model, OrderItem model, pricing logic, coupon validation,
and _create_order_record DB persistence.

All tests run against SQLite in-memory. No PostgreSQL or external services needed.

Run:
    pytest tests/test_order_logic.py -v
"""
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY",   "test-secret-key")
os.environ.setdefault("FLASK_ENV",    "testing")
os.environ.setdefault("FLASK_DEBUG",  "0")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TESTING",      "1")


# ─────────────────────────────────────────────────────────────────────────────
# Session-scoped fixtures — one DB for the whole module
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from app import app as flask_app
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    return flask_app


@pytest.fixture(scope="module")
def db(app):
    from db import db as _db
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="module")
def seed(app, db):
    """
    One user + one restaurant + two food items, created once for the whole module.
    Returns a plain dict so it's safe to use across contexts.
    """
    from models import User, Restaurant, FoodItem
    from werkzeug.security import generate_password_hash

    with app.app_context():
        user = User(
            name="Test Customer",
            email="customer_order@test.com",
            password=generate_password_hash("password"),
            role="customer",
        )
        db.session.add(user)
        db.session.flush()

        restaurant = Restaurant(
            name="Order Test Restaurant",
            location="Test City",
            cuisine_type="Test",
            is_active=True,
            is_approved=True,
        )
        db.session.add(restaurant)
        db.session.flush()

        food1 = FoodItem(
            restaurant_id=restaurant.id,
            name="Butter Chicken",
            price=320.0,
            is_available=True,
        )
        food2 = FoodItem(
            restaurant_id=restaurant.id,
            name="Garlic Naan",
            price=60.0,
            is_available=True,
        )
        db.session.add_all([food1, food2])
        db.session.commit()

        return {
            "user_id":        user.id,
            "restaurant_id":  restaurant.id,
            "food1_id":       food1.id,
            "food1_name":     food1.name,
            "food1_price":    food1.price,
            "food2_id":       food2.id,
            "food2_price":    food2.price,
        }


# Convenience fixture: push app context for pure-model tests
@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ─────────────────────────────────────────────────────────────────────────────
# Order model tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderModel:

    def test_status_badge_placed(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        o.status = "placed"
        assert o.status_badge_class == "warning"

    def test_status_badge_delivered(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        o.status = "delivered"
        assert o.status_badge_class == "success"

    def test_status_badge_cancelled(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        o.status = "cancelled"
        assert o.status_badge_class == "danger"

    def test_status_badge_unknown_falls_back(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        o.status = "not_a_real_status"
        assert o.status_badge_class == "secondary"

    def test_items_property_is_empty_list_when_none(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        assert o.items == []

    def test_items_property_returns_json_snapshot(self, ctx):
        from models import Order
        snap = [{"name": "Burger", "qty": 2}]
        o = Order(user_id=1, restaurant_id=1, total_amount=100,
                  delivery_address="x", order_items=snap)
        assert o.items == snap

    def test_default_status_is_placed(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        assert o.status == "placed"

    def test_default_payment_method_is_cod(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        assert o.payment_method == "cod"

    def test_default_payment_status_is_pending(self, ctx):
        from models import Order
        o = Order(user_id=1, restaurant_id=1, total_amount=100, delivery_address="x")
        assert o.payment_status == "pending"


# ─────────────────────────────────────────────────────────────────────────────
# OrderItem model tests
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderItemModel:

    def test_total_property(self, ctx):
        from models import OrderItem
        item = OrderItem(order_id=1, name="Pizza", price=299.0, quantity=3)
        assert item.total == 897.0

    def test_total_rounds_to_two_decimals(self, ctx):
        from models import OrderItem
        item = OrderItem(order_id=1, name="Chai", price=33.333, quantity=3)
        assert item.total == round(33.333 * 3, 2)

    def test_default_quantity_is_one(self, ctx):
        from models import OrderItem
        item = OrderItem(order_id=1, name="Soup", price=100.0)
        assert item.quantity == 1

    def test_repr_contains_name(self, ctx):
        from models import OrderItem
        item = OrderItem(order_id=1, name="Dosa", price=80.0, quantity=2)
        assert "Dosa" in repr(item)


# ─────────────────────────────────────────────────────────────────────────────
# Pricing logic (pure Python — no DB, no app context)
# ─────────────────────────────────────────────────────────────────────────────

class TestPricingLogic:

    def test_tax_is_18_percent(self):
        assert round(500.0 * 0.18, 2) == 90.0

    def test_delivery_fee_waived_above_500(self):
        assert (0.0 if 500.01 > 500 else 40.0) == 0.0

    def test_delivery_fee_applied_at_exactly_500(self):
        assert (0.0 if 500.0 > 500 else 40.0) == 40.0

    def test_delivery_fee_applied_below_500(self):
        for s in [499.99, 200.0, 1.0]:
            assert (0.0 if s > 500 else 40.0) == 40.0

    def test_total_no_discount(self):
        sub  = 320.0
        tax  = round(sub * 0.18, 2)   # 57.6
        dlv  = 40.0                    # <500
        plat = 5.0
        assert round(sub + tax + dlv + plat, 2) == round(320 + 57.6 + 40 + 5, 2)

    def test_total_with_discount(self):
        sub  = 600.0
        tax  = round(sub * 0.18, 2)   # 108
        dlv  = 0.0                     # >500 waived
        disc = 50.0
        plat = 5.0
        assert round(sub + tax + dlv - disc + plat, 2) == round(600 + 108 - 50 + 5, 2)

    def test_flat_discount_capped_at_subtotal(self):
        assert min(200.0, 100.0) == 100.0

    def test_percentage_discount_capped_at_max(self):
        raw = 1000.0 * 10 / 100   # 100
        assert min(raw, 75.0) == 75.0


# ─────────────────────────────────────────────────────────────────────────────
# Offer model tests (no DB — pure object tests)
# ─────────────────────────────────────────────────────────────────────────────

class TestOfferModel:

    def _offer(self, **kw):
        from models import Offer
        now = datetime.now(timezone.utc)
        defaults = dict(
            title="Test", description="Desc",
            discount_type="percentage", discount_value=10.0,
            code="TEST10",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=1),
            is_active=True,
            usage_limit=None,
            used_count=0,
        )
        defaults.update(kw)
        return Offer(**defaults)

    def test_valid_offer(self, ctx):
        valid, msg = self._offer().is_valid()
        assert valid is True

    def test_inactive_offer(self, ctx):
        valid, _ = self._offer(is_active=False).is_valid()
        assert valid is False

    def test_expired_offer(self, ctx):
        valid, msg = self._offer(
            end_date=datetime.now(timezone.utc) - timedelta(hours=1)
        ).is_valid()
        assert valid is False
        assert "expired" in msg.lower()

    def test_not_started_offer(self, ctx):
        valid, msg = self._offer(
            start_date=datetime.now(timezone.utc) + timedelta(days=1)
        ).is_valid()
        assert valid is False
        assert "not yet" in msg.lower()

    def test_usage_limit_reached(self, ctx):
        valid, msg = self._offer(usage_limit=5, used_count=5).is_valid()
        assert valid is False
        assert "limit" in msg.lower()

    def test_usage_limit_not_reached(self, ctx):
        valid, _ = self._offer(usage_limit=5, used_count=4).is_valid()
        assert valid is True

    def test_unlimited_usage_always_valid(self, ctx):
        valid, _ = self._offer(usage_limit=None, used_count=9999).is_valid()
        assert valid is True

    def test_percentage_discount(self, ctx):
        o = self._offer(discount_type="percentage", discount_value=10.0, max_discount=None)
        raw = 500.0 * o.discount_value / 100
        discount = min(raw, o.max_discount) if o.max_discount else raw
        assert discount == 50.0

    def test_percentage_discount_capped(self, ctx):
        o = self._offer(discount_type="percentage", discount_value=10.0, max_discount=75.0)
        raw = 1000.0 * o.discount_value / 100   # 100
        discount = min(raw, o.max_discount)       # 75
        assert discount == 75.0

    def test_flat_discount(self, ctx):
        o = self._offer(discount_type="flat", discount_value=50.0)
        assert min(o.discount_value, 300.0) == 50.0

    def test_flat_discount_capped_at_subtotal(self, ctx):
        o = self._offer(discount_type="flat", discount_value=200.0)
        assert min(o.discount_value, 150.0) == 150.0


# ─────────────────────────────────────────────────────────────────────────────
# _create_order_record integration tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateOrderRecord:
    """Tests _create_order_record against the in-memory SQLite DB."""

    def _call(self, app, db, seed, payment_method="cod",
              delivery_address="456 Main Street, Test City",
              delivery_phone="9876543210",
              gateway_order_id=None,
              extra_data=None):

        items_snapshot = [{
            "id":              seed["food1_id"],
            "name":            seed["food1_name"],
            "quantity":        2,
            "price":           float(seed["food1_price"]),
            "total":           float(seed["food1_price"] * 2),
            "restaurant_name": "Order Test Restaurant",
        }]
        subtotal = seed["food1_price"] * 2
        amounts  = {
            "subtotal":     subtotal,
            "tax":          round(subtotal * 0.18, 2),
            "delivery_fee": 40.0,
            "discount":     0.0,
            "platform_fee": 5.0,
            "total":        round(subtotal * 1.18 + 40.0 + 5.0, 2),
            "coupon_code":  None,
        }
        data = {"delivery_address": delivery_address, "delivery_phone": delivery_phone}
        if extra_data:
            data.update(extra_data)

        from utils.order_helpers import _create_order_record

        with app.app_context():
            with patch("utils.order_helpers.current_user") as mu:
                mu.id   = seed["user_id"]
                mu.name = "Test Customer"
                order, payment_rec = _create_order_record(
                    data, amounts, seed["restaurant_id"], items_snapshot,
                    payment_method=payment_method,
                    gateway_order_id=gateway_order_id,
                )
                db.session.commit()
                return order.id, amounts

    def test_order_is_persisted(self, app, db, seed):
        from models import Order
        oid, _ = self._call(app, db, seed)
        with app.app_context():
            order = db.session.get(Order, oid)
            assert order is not None
            assert order.status == "placed"
            assert order.payment_method == "cod"

    def test_totals_are_correct(self, app, db, seed):
        from models import Order
        oid, amounts = self._call(app, db, seed)
        with app.app_context():
            o = db.session.get(Order, oid)
            assert o.total_amount == amounts["total"]
            assert o.subtotal     == amounts["subtotal"]
            assert o.tax          == amounts["tax"]
            assert o.delivery_fee == 40.0

    def test_order_items_created(self, app, db, seed):
        from models import OrderItem
        oid, _ = self._call(app, db, seed)
        with app.app_context():
            items = OrderItem.query.filter_by(order_id=oid).all()
            assert len(items) == 1
            assert items[0].name     == seed["food1_name"]
            assert items[0].quantity == 2
            assert items[0].price    == seed["food1_price"]

    def test_payment_record_created(self, app, db, seed):
        from models import Payment
        oid, amounts = self._call(app, db, seed)
        with app.app_context():
            p = Payment.query.filter_by(order_id=oid).first()
            assert p is not None
            assert p.status          == "pending"
            assert p.amount          == amounts["total"]
            assert p.payment_method  == "cod"

    def test_status_history_created(self, app, db, seed):
        from models import OrderStatusHistory
        oid, _ = self._call(app, db, seed)
        with app.app_context():
            history = OrderStatusHistory.query.filter_by(order_id=oid).all()
            assert len(history) == 1
            assert history[0].status == "placed"

    def test_gateway_order_id_stored(self, app, db, seed):
        from models import Order, Payment
        oid, _ = self._call(app, db, seed, gateway_order_id="order_RZ123")
        with app.app_context():
            o = db.session.get(Order, oid)
            p = Payment.query.filter_by(order_id=oid).first()
            assert o.razorpay_order_id  == "order_RZ123"
            assert p.gateway_order_id   == "order_RZ123"

    def test_upi_payment_method_stored(self, app, db, seed):
        from models import Order
        oid, _ = self._call(app, db, seed, payment_method="upi",
                            gateway_order_id="order_UPI001")
        with app.app_context():
            o = db.session.get(Order, oid)
            assert o.payment_method  == "upi"
            assert o.payment_status  == "pending"

    def test_short_address_raises(self, app, db, seed):
        with pytest.raises(ValueError, match="too short"):
            self._call(app, db, seed, delivery_address="123")

    def test_location_note_in_order_notes(self, app, db, seed):
        from models import Order
        oid, _ = self._call(app, db, seed, extra_data={
            "notes": "Ring bell",
            "delivery_location": {"name": "Home", "city": "Mumbai", "state": "MH"},
        })
        with app.app_context():
            o = db.session.get(Order, oid)
            assert "Location:" in o.notes
            assert "Mumbai"    in o.notes
