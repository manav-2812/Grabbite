"""
Grabbite — Payment Blueprint
Handles payment pages, COD, Razorpay order creation, payment verification,
and Razorpay server-to-server webhooks.

Plan 5 refactor: private helpers moved to:
  utils/order_helpers.py    — _build_order_from_cart, _create_order_record, _post_order_notifications
  utils/razorpay_helpers.py — _get_razorpay_client, verify_razorpay_signature, verify_webhook_signature
"""
import os
from datetime import datetime, timezone

from flask import (Blueprint, render_template, request, redirect,
                   url_for, jsonify, current_app)
from flask_login import current_user, login_required

from db import db
from models import (Order, Cart, Payment, OrderStatusHistory,
                    Notification, AdminNotification)
from utils.order_helpers import (
    _build_order_from_cart, _create_order_record, _post_order_notifications,
)
from utils.razorpay_helpers import (
    _get_razorpay_client, verify_razorpay_signature, verify_webhook_signature,
)

payment_bp = Blueprint('payment', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT PAGES
# ─────────────────────────────────────────────────────────────────────────────

@payment_bp.route('/payment/success/<int:order_id>')
@login_required
def payment_success(order_id):
    order   = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    payment = Payment.query.filter_by(order_id=order_id).order_by(Payment.id.desc()).first()
    return render_template('payment_success.html', order=order, payment=payment)


@payment_bp.route('/payment/failed')
@login_required
def payment_failed():
    order_id = request.args.get('order_id', type=int)
    order = None
    if order_id:
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    return render_template('payment_failed.html', order=order)


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT APIs
# ─────────────────────────────────────────────────────────────────────────────

@payment_bp.route('/api/orders/place', methods=['POST'])
@login_required
def place_order():
    """Deprecated: use /api/payment/cod instead. Kept for backward compatibility."""
    current_app.logger.info('Deprecated /api/orders/place called — delegating to payment_cod')
    return payment_cod()


@payment_bp.route('/api/payment/cod', methods=['POST'])
@login_required
def payment_cod():
    """Place a Cash on Delivery order directly."""
    try:
        data = request.get_json() or {}
        if not data.get('delivery_address') or not data.get('delivery_phone'):
            return jsonify({'success': False, 'message': 'Delivery address and phone required'}), 400

        cart_rows, amounts, restaurant_id, items = _build_order_from_cart(data)
        order, _ = _create_order_record(data, amounts, restaurant_id, items,
                                         payment_method='cod', payment_status='pending')
        Cart.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        _post_order_notifications(order, amounts)

        return jsonify({'success': True, 'order_id': order.id,
                        'redirect': url_for('payment.payment_success', order_id=order.id)})
    except ValueError as ve:
        return jsonify({'success': False, 'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'payment_cod error: {e}')
        return jsonify({'success': False, 'message': 'Failed to place order'}), 500


@payment_bp.route('/api/payment/create-razorpay-order', methods=['POST'])
@login_required
def create_razorpay_order():
    """Create a Razorpay order and a pending Order record. Returns gateway details to frontend."""
    try:
        data = request.get_json() or {}
        if not data.get('delivery_address') or not data.get('delivery_phone'):
            return jsonify({'success': False, 'message': 'Delivery address and phone required'}), 400

        rz = _get_razorpay_client()
        if not rz:
            return jsonify({
                'success': False,
                'message': 'Online payments not configured. Please use Cash on Delivery.',
                'fallback_cod': True,
            }), 400

        cart_rows, amounts, restaurant_id, items = _build_order_from_cart(data)
        payment_method = data.get('payment_method', 'upi')

        rz_order = rz.order.create({
            'amount':   int(amounts['total'] * 100),
            'currency': 'INR',
            'receipt':  f'gb_{current_user.id}_{int(datetime.now().timestamp())}',
            'notes':    {'user_id': str(current_user.id), 'source': 'grabbite'},
        })

        order, _ = _create_order_record(data, amounts, restaurant_id, items,
                                          payment_method=payment_method,
                                          payment_status='pending',
                                          gateway_order_id=rz_order['id'])
        db.session.commit()

        return jsonify({
            'success':           True,
            'razorpay_key':      current_app.config['RAZORPAY_KEY_ID'],
            'razorpay_order_id': rz_order['id'],
            'amount':            rz_order['amount'],
            'currency':          rz_order['currency'],
            'order_id':          order.id,
            'prefill': {
                'name':    current_user.name,
                'email':   current_user.email,
                'contact': data.get('delivery_phone', ''),
            },
        })
    except ValueError as ve:
        return jsonify({'success': False, 'message': str(ve)}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'create_razorpay_order error: {e}')
        return jsonify({'success': False, 'message': 'Failed to create payment order'}), 500


@payment_bp.route('/api/payment/verify', methods=['POST'])
@login_required
def verify_payment():
    """Verify Razorpay HMAC-SHA256 signature and confirm the order as paid."""
    try:
        data          = request.get_json() or {}
        rz_order_id   = data.get('razorpay_order_id', '')
        rz_payment_id = data.get('razorpay_payment_id', '')
        rz_signature  = data.get('razorpay_signature', '')
        order_id      = data.get('order_id')

        if not all([rz_order_id, rz_payment_id, rz_signature, order_id]):
            return jsonify({'success': False, 'message': 'Incomplete payment data'}), 400

        if not verify_razorpay_signature(rz_order_id, rz_payment_id, rz_signature):
            current_app.logger.warning(f'Payment signature mismatch for order {order_id}')
            return jsonify({'success': False, 'message': 'Payment verification failed'}), 400

        from sqlalchemy import update
        now  = datetime.now(timezone.utc)
        stmt = (
            update(Order)
            .where(Order.id == order_id)
            .where(Order.user_id == current_user.id)
            .where(Order.payment_status != 'paid')
            .values(
                payment_status='paid',
                razorpay_payment_id=rz_payment_id,
                razorpay_order_id=rz_order_id,
            )
        )
        result = db.session.execute(stmt)
        if result.rowcount == 0:
            db.session.rollback()
            order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
            if not order:
                return jsonify({'success': False, 'message': 'Order not found'}), 404
            return jsonify({'success': True, 'order_id': order.id,
                            'redirect': url_for('payment.payment_success', order_id=order.id)})

        db.session.expire_all()
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Order not found'}), 404

        payment_rec = Payment.query.filter_by(
            order_id=order_id, gateway_order_id=rz_order_id
        ).first()
        if payment_rec:
            payment_rec.gateway_payment_id = rz_payment_id
            payment_rec.gateway_signature  = rz_signature
            payment_rec.status             = 'paid'
            payment_rec.transaction_id     = rz_payment_id
        else:
            db.session.add(Payment(
                order_id=order_id,
                user_id=current_user.id,
                amount=order.total_amount,
                payment_method=order.payment_method,
                gateway_order_id=rz_order_id,
                gateway_payment_id=rz_payment_id,
                gateway_signature=rz_signature,
                transaction_id=rz_payment_id,
                status='paid',
            ))

        Cart.query.filter_by(user_id=current_user.id).delete()

        db.session.add(OrderStatusHistory(
            order_id=order.id, status='placed',
            note=f'Payment confirmed via Razorpay ({rz_payment_id})'
        ))
        db.session.add(AdminNotification(
            title='Payment Received',
            message=f'Order #{order.id} paid ₹{order.total_amount} via {order.payment_method}',
            type='order',
        ))
        db.session.add(Notification(
            user_id=current_user.id,
            title='Payment Successful! ✅',
            message=f'₹{order.total_amount} paid for Order #{order.id}',
            type='order_update',
            link=url_for('account.orders'),
        ))
        db.session.commit()

        return jsonify({'success': True, 'order_id': order.id,
                        'redirect': url_for('payment.payment_success', order_id=order.id)})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'verify_payment error: {e}')
        return jsonify({'success': False, 'message': 'Payment verification error'}), 500


@payment_bp.route('/api/payment/webhook', methods=['POST'])
def razorpay_webhook():
    """Razorpay server-to-server webhook. Verified by X-Razorpay-Signature header."""
    try:
        webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
        if not webhook_secret:
            if os.environ.get('FLASK_ENV', 'development') == 'production':
                current_app.logger.error(
                    'RAZORPAY_WEBHOOK_SECRET is not set in production — '
                    'rejecting webhook to avoid processing unsigned events.'
                )
                return jsonify({'error': 'webhook not configured'}), 503
            current_app.logger.warning(
                'RAZORPAY_WEBHOOK_SECRET is empty — accepting webhook in '
                'development mode. Set the secret before going to production.'
            )

        received_sig = request.headers.get('X-Razorpay-Signature', '')
        body         = request.get_data()
        if not verify_webhook_signature(body, received_sig, webhook_secret):
            current_app.logger.warning('Webhook signature verification failed')
            return jsonify({'error': 'Invalid signature'}), 400

        payload = request.get_json(force=True) or {}
        event   = payload.get('event', '')

        if event == 'payment.captured':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            rz_payment_id  = payment_entity.get('id')
            rz_order_id    = payment_entity.get('order_id')

            if rz_order_id:
                order = Order.query.filter_by(razorpay_order_id=rz_order_id).first()
                if order and order.payment_status != 'paid':
                    order.payment_status      = 'paid'
                    order.razorpay_payment_id = rz_payment_id
                    p = Payment.query.filter_by(gateway_order_id=rz_order_id).first()
                    if p:
                        p.status             = 'paid'
                        p.gateway_payment_id = rz_payment_id
                        p.transaction_id     = rz_payment_id
                    db.session.commit()

        elif event == 'payment.failed':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            rz_order_id    = payment_entity.get('order_id')
            if rz_order_id:
                order = Order.query.filter_by(razorpay_order_id=rz_order_id).first()
                if order and order.payment_status == 'pending':
                    order.payment_status = 'failed'
                    p = Payment.query.filter_by(gateway_order_id=rz_order_id).first()
                    if p:
                        p.status = 'failed'
                    db.session.commit()

        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        current_app.logger.error(f'webhook error: {e}')
        return jsonify({'status': 'error'}), 500
