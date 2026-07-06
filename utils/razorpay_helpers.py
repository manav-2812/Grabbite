"""
Grabbite — utils/razorpay_helpers.py
Plan 5 refactor: Razorpay client factory extracted from blueprints/payment.py.

Provides:
  _get_razorpay_client — returns a configured Razorpay client or None
  verify_razorpay_signature — HMAC-SHA256 signature verification
"""
import hmac
import hashlib

from flask import current_app


def _get_razorpay_client():
    """Return a Razorpay client or None if unavailable/unconfigured."""
    try:
        import razorpay as _rz
    except ImportError:
        return None
    key_id     = current_app.config.get('RAZORPAY_KEY_ID', '')
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '')
    if not key_id or not key_secret or 'xxx' in key_secret.lower():
        return None
    try:
        return _rz.Client(auth=(key_id, key_secret))
    except Exception as exc:
        current_app.logger.warning(f'Razorpay client init failed: {exc}')
        return None


def verify_razorpay_signature(rz_order_id: str, rz_payment_id: str, signature: str) -> bool:
    """Verify a Razorpay HMAC-SHA256 payment signature.

    Returns True if the signature is valid, False otherwise.
    """
    key_secret = current_app.config.get('RAZORPAY_KEY_SECRET', '').encode()
    msg        = f'{rz_order_id}|{rz_payment_id}'.encode()
    expected   = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_webhook_signature(body: bytes, received_sig: str, secret: str) -> bool:
    """Verify a Razorpay webhook HMAC-SHA256 signature."""
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_sig)
