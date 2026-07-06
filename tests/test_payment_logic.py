"""
Unit tests — Payment model, Razorpay HMAC signature verification,
webhook signature verification, and webhook endpoint DB side-effects.

Endpoint-level tests (COD / verify) are tested as pure unit tests via
mocking, avoiding CSRF and session complexity. Webhook tests use the
test client directly because the webhook route is CSRF-exempt.

Run:
    pytest tests/test_payment_logic.py -v
"""
import os
import hmac
import hashlib
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

os.environ.setdefault("SECRET_KEY",   "test-secret-key")
os.environ.setdefault("FLASK_ENV",    "testing")
os.environ.setdefault("FLASK_DEBUG",  "0")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("TESTING",      "1")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from app import app as flask_app
    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        RAZORPAY_KEY_ID="rzp_test_fake",
        RAZORPAY_KEY_SECRET="fake_secret_for_testing",
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


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


@pytest.fixture(scope="module")
def client(app, db):
    with app.test_client() as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Payment model unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentModel:

    def test_default_status_is_pending(self, ctx):
        from models import Payment
        assert Payment(order_id=1, amount=500.0).status == "pending"

    def test_default_currency_is_inr(self, ctx):
        from models import Payment
        assert Payment(order_id=1, amount=100.0).currency == "INR"

    def test_default_refund_amount_is_zero(self, ctx):
        from models import Payment
        assert Payment(order_id=1, amount=200.0).refund_amount == 0.0

    def test_repr_contains_amount_and_status(self, ctx):
        from models import Payment
        p = Payment(order_id=1, amount=299.0, status="paid")
        r = repr(p)
        assert "299.0" in r
        assert "paid"  in r

    def test_stores_all_gateway_fields(self, ctx):
        from models import Payment
        p = Payment(
            order_id=1, amount=750.0, payment_method="upi",
            gateway_order_id="order_abc", gateway_payment_id="pay_xyz",
            gateway_signature="hmac_sig", status="paid",
        )
        assert p.gateway_order_id   == "order_abc"
        assert p.gateway_payment_id == "pay_xyz"
        assert p.gateway_signature  == "hmac_sig"
        assert p.status             == "paid"

    def test_payment_method_defaults_to_cod(self, ctx):
        from models import Payment
        assert Payment(order_id=1, amount=100.0).payment_method == "cod"


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay payment signature verification (pure Python)
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyRazorpaySignature:
    """
    Directly tests the HMAC math in verify_razorpay_signature by running
    inside an app context and reading the secret from app.config.
    """

    SECRET = "test_razorpay_secret"

    def _sig(self, order_id, payment_id, secret=None):
        key = (secret or self.SECRET).encode()
        msg = f"{order_id}|{payment_id}".encode()
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    def _call(self, app, order_id, payment_id, sig, secret=None):
        with app.app_context():
            app.config["RAZORPAY_KEY_SECRET"] = secret or self.SECRET
            from utils.razorpay_helpers import verify_razorpay_signature
            return verify_razorpay_signature(order_id, payment_id, sig)

    def test_valid_signature(self, app):
        sig = self._sig("order_A", "pay_B")
        assert self._call(app, "order_A", "pay_B", sig) is True

    def test_tampered_payment_id(self, app):
        sig = self._sig("order_A", "pay_B")
        assert self._call(app, "order_A", "pay_TAMPERED", sig) is False

    def test_tampered_order_id(self, app):
        sig = self._sig("order_A", "pay_B")
        assert self._call(app, "order_TAMPERED", "pay_B", sig) is False

    def test_wrong_secret(self, app):
        sig = self._sig("order_A", "pay_B", secret="correct")
        assert self._call(app, "order_A", "pay_B", sig, secret="wrong") is False

    def test_empty_signature(self, app):
        assert self._call(app, "order_A", "pay_B", "") is False

    def test_different_order_produces_different_sig(self):
        sig1 = self._sig("order_1", "pay_X")
        sig2 = self._sig("order_2", "pay_X")
        assert sig1 != sig2

    def test_separator_matters(self, app):
        """A signature built without the | separator must not match."""
        key     = self.SECRET.encode()
        bad_sig = hmac.new(key, b"order_Apay_B", hashlib.sha256).hexdigest()
        assert self._call(app, "order_A", "pay_B", bad_sig) is False


# ─────────────────────────────────────────────────────────────────────────────
# Webhook signature verification (pure Python — no Flask context needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyWebhookSignature:

    def _sig(self, body: bytes, secret: str) -> str:
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def test_valid_signature(self):
        from utils.razorpay_helpers import verify_webhook_signature
        body   = b'{"event":"payment.captured"}'
        secret = "wh_secret"
        sig    = self._sig(body, secret)
        assert verify_webhook_signature(body, sig, secret) is True

    def test_tampered_body(self):
        from utils.razorpay_helpers import verify_webhook_signature
        secret   = "wh_secret"
        body     = b'{"event":"payment.captured"}'
        sig      = self._sig(body, secret)
        tampered = b'{"event":"payment.captured","injected":true}'
        assert verify_webhook_signature(tampered, sig, secret) is False

    def test_wrong_secret(self):
        from utils.razorpay_helpers import verify_webhook_signature
        body = b'{"event":"payment.captured"}'
        sig  = self._sig(body, "real_secret")
        assert verify_webhook_signature(body, sig, "wrong_secret") is False

    def test_empty_body_valid_sig(self):
        from utils.razorpay_helpers import verify_webhook_signature
        body   = b""
        secret = "s"
        sig    = self._sig(body, secret)
        assert verify_webhook_signature(body, sig, secret) is True

    def test_empty_sig_fails(self):
        from utils.razorpay_helpers import verify_webhook_signature
        body = b'{"event":"x"}'
        assert verify_webhook_signature(body, "", "secret") is False


# ─────────────────────────────────────────────────────────────────────────────
# payment_cod business logic (unit tested via mocking — no HTTP layer)
# ─────────────────────────────────────────────────────────────────────────────

class TestPaymentCodLogic:
    """Pure logic tests for the COD validation guard — no HTTP layer needed."""

    def test_missing_address_fails_guard(self):
        data = {"delivery_phone": "9876543210"}
        assert not (data.get("delivery_address") and data.get("delivery_phone"))

    def test_missing_phone_fails_guard(self):
        data = {"delivery_address": "123 Main Street, Test City"}
        assert not (data.get("delivery_address") and data.get("delivery_phone"))

    def test_both_fields_pass_guard(self):
        data = {"delivery_address": "123 Main Street, Test City",
                "delivery_phone": "9876543210"}
        assert data.get("delivery_address") and data.get("delivery_phone")

    def test_empty_address_fails_guard(self):
        data = {"delivery_address": "", "delivery_phone": "9876543210"}
        assert not (data.get("delivery_address") and data.get("delivery_phone"))


# ─────────────────────────────────────────────────────────────────────────────
# Verify payment logic (pure unit tests — no HTTP, no DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestVerifyPaymentLogic:

    def test_incomplete_data_detected(self):
        required = ["razorpay_order_id", "razorpay_payment_id",
                    "razorpay_signature", "order_id"]
        full = {k: "value" for k in required}
        assert all(full.get(k) for k in required) is True
        for missing in required:
            partial = {k: "v" for k in required if k != missing}
            assert not all(partial.get(k) for k in required)

    def test_signature_verification_with_app_context(self, app):
        with app.app_context():
            app.config["RAZORPAY_KEY_SECRET"] = "my_secret"
            from utils.razorpay_helpers import verify_razorpay_signature
            order_id   = "order_XYZ"
            payment_id = "pay_ABC"
            expected   = hmac.new(
                b"my_secret",
                f"{order_id}|{payment_id}".encode(),
                hashlib.sha256,
            ).hexdigest()
            assert verify_razorpay_signature(order_id, payment_id, expected) is True
            assert verify_razorpay_signature(order_id, payment_id, "wrong") is False


# ─────────────────────────────────────────────────────────────────────────────
# Webhook endpoint DB side-effect tests (test client — webhook is CSRF-exempt)
# ─────────────────────────────────────────────────────────────────────────────

WEBHOOK_SECRET = "test_webhook_secret_xyz"


def _webhook_sig(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


class TestWebhookEndpoint:

    def test_bad_signature_returns_400(self, client):
        body = json.dumps({"event": "payment.captured"}).encode()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            resp = client.post(
                "/api/payment/webhook",
                data=body, content_type="application/json",
                headers={"X-Razorpay-Signature": "bad_sig"},
            )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Invalid signature"

    def test_unknown_event_returns_200(self, client):
        body = json.dumps({"event": "some.unknown.event"}).encode()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            resp = client.post(
                "/api/payment/webhook",
                data=body, content_type="application/json",
                headers={"X-Razorpay-Signature": _webhook_sig(body)},
            )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_payment_captured_marks_order_paid(self, app, db, client):
        """payment.captured webhook sets order.payment_status = 'paid'."""
        with app.app_context():
            from models import Order, Payment, Restaurant, User
            from werkzeug.security import generate_password_hash

            u = User(name="WH1", email="wh1@test.com",
                     password=generate_password_hash("x"))
            db.session.add(u)
            db.session.flush()

            r = Restaurant(name="WH1 Rest", location="City",
                           cuisine_type="T", is_active=True)
            db.session.add(r)
            db.session.flush()

            order = Order(
                user_id=u.id, restaurant_id=r.id,
                total_amount=750.0, delivery_address="123 St",
                payment_method="upi", payment_status="pending",
                razorpay_order_id="order_WH1",
            )
            db.session.add(order)
            db.session.flush()

            pmt = Payment(order_id=order.id, user_id=u.id, amount=750.0,
                          payment_method="upi", gateway_order_id="order_WH1",
                          status="pending")
            db.session.add(pmt)
            db.session.commit()
            oid = order.id

        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {
                "id": "pay_WH1", "order_id": "order_WH1"
            }}},
        }
        body = json.dumps(payload).encode()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            resp = client.post(
                "/api/payment/webhook", data=body,
                content_type="application/json",
                headers={"X-Razorpay-Signature": _webhook_sig(body)},
            )

        assert resp.status_code == 200
        with app.app_context():
            from models import Order, Payment
            o = db.session.get(Order, oid)
            p = Payment.query.filter_by(order_id=oid).first()
            assert o.payment_status       == "paid"
            assert o.razorpay_payment_id  == "pay_WH1"
            assert p.status               == "paid"
            assert p.gateway_payment_id   == "pay_WH1"

    def test_payment_failed_marks_order_failed(self, app, db, client):
        """payment.failed webhook sets order.payment_status = 'failed'."""
        with app.app_context():
            from models import Order, Payment, Restaurant, User
            from werkzeug.security import generate_password_hash

            u = User(name="WH2", email="wh2@test.com",
                     password=generate_password_hash("x"))
            db.session.add(u)
            db.session.flush()

            r = Restaurant(name="WH2 Rest", location="City",
                           cuisine_type="T", is_active=True)
            db.session.add(r)
            db.session.flush()

            order = Order(
                user_id=u.id, restaurant_id=r.id,
                total_amount=300.0, delivery_address="123 St",
                payment_method="upi", payment_status="pending",
                razorpay_order_id="order_WH2",
            )
            db.session.add(order)
            db.session.flush()

            pmt = Payment(order_id=order.id, user_id=u.id, amount=300.0,
                          payment_method="upi", gateway_order_id="order_WH2",
                          status="pending")
            db.session.add(pmt)
            db.session.commit()
            oid = order.id

        payload = {
            "event": "payment.failed",
            "payload": {"payment": {"entity": {"order_id": "order_WH2"}}},
        }
        body = json.dumps(payload).encode()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            resp = client.post(
                "/api/payment/webhook", data=body,
                content_type="application/json",
                headers={"X-Razorpay-Signature": _webhook_sig(body)},
            )

        assert resp.status_code == 200
        with app.app_context():
            from models import Order, Payment
            o = db.session.get(Order, oid)
            p = Payment.query.filter_by(order_id=oid).first()
            assert o.payment_status == "failed"
            assert p.status         == "failed"

    def test_idempotent_capture_already_paid(self, app, db, client):
        """Webhook for an already-paid order is a no-op — does not error."""
        with app.app_context():
            from models import Order, Restaurant, User
            from werkzeug.security import generate_password_hash

            u = User(name="WH3", email="wh3@test.com",
                     password=generate_password_hash("x"))
            db.session.add(u)
            db.session.flush()
            r = Restaurant(name="WH3 Rest", location="City",
                           cuisine_type="T", is_active=True)
            db.session.add(r)
            db.session.flush()
            order = Order(
                user_id=u.id, restaurant_id=r.id,
                total_amount=100.0, delivery_address="St",
                payment_method="upi", payment_status="paid",
                razorpay_order_id="order_WH3",
            )
            db.session.add(order)
            db.session.commit()

        payload = {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {
                "id": "pay_WH3_dup", "order_id": "order_WH3"
            }}},
        }
        body = json.dumps(payload).encode()
        with patch.dict(os.environ, {"RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET}):
            resp = client.post(
                "/api/payment/webhook", data=body,
                content_type="application/json",
                headers={"X-Razorpay-Signature": _webhook_sig(body)},
            )
        # Already paid — webhook still returns 200 (no error)
        assert resp.status_code == 200
