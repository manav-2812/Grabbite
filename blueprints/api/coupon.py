"""
Grabbite — API: Coupon
/api/coupon/apply, /api/coupon/validate
"""
from flask import request, jsonify
from flask_login import current_user, login_required

from models import Offer, CouponUsage
from blueprints.api import api_bp


@api_bp.route('/api/coupon/apply', methods=['POST'])
@login_required
def api_coupon_apply():
    data       = request.get_json() or {}
    code       = (data.get('code') or '').strip().upper()
    cart_total = float(data.get('cart_total', 0))

    if not code:
        return jsonify({'success': False, 'message': 'Coupon code required'}), 400

    offer = Offer.query.filter_by(code=code).first()
    if not offer:
        return jsonify({'success': False, 'message': 'Invalid coupon code'}), 404

    valid, msg = offer.is_valid()
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400

    if cart_total < offer.min_order_amount:
        return jsonify({
            'success': False,
            'message': f'Min order ₹{offer.min_order_amount} required for this coupon',
        }), 400

    already_used = CouponUsage.query.filter_by(
        offer_id=offer.id, user_id=current_user.id
    ).first()
    if already_used:
        return jsonify({'success': False, 'message': 'You have already used this coupon'}), 400

    if offer.discount_type == 'percentage':
        discount = cart_total * (offer.discount_value / 100)
    else:
        discount = offer.discount_value

    if offer.max_discount:
        discount = min(discount, offer.max_discount)

    return jsonify({
        'success':        True,
        'message':        f'Coupon applied! You save ₹{discount:.2f}',
        'discount':       round(discount, 2),
        'discount_type':  offer.discount_type,
        'discount_value': offer.discount_value,
        'code':           offer.code,
    })


@api_bp.route('/api/coupon/validate', methods=['POST'])
@login_required
def api_coupon_validate():
    """Alias for /api/coupon/apply — used by the checkout page."""
    data = request.get_json() or {}
    if 'subtotal' in data and 'cart_total' not in data:
        data['cart_total'] = data['subtotal']
    code       = (data.get('code') or '').strip().upper()
    cart_total = float(data.get('cart_total', 0))

    if not code:
        return jsonify({'success': False, 'message': 'Coupon code required'}), 400
    offer = Offer.query.filter_by(code=code).first()
    if not offer:
        return jsonify({'success': False, 'message': 'Invalid coupon code'}), 404
    valid, msg = offer.is_valid()
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400
    if cart_total < offer.min_order_amount:
        return jsonify({'success': False, 'message': f'Min order ₹{offer.min_order_amount:.0f} required'}), 400
    already_used = CouponUsage.query.filter_by(offer_id=offer.id, user_id=current_user.id).first()
    if already_used:
        return jsonify({'success': False, 'message': 'You have already used this coupon'}), 400
    if offer.discount_type == 'percentage':
        discount = cart_total * (offer.discount_value / 100)
    else:
        discount = offer.discount_value
    if offer.max_discount:
        discount = min(discount, offer.max_discount)
    return jsonify({'success': True, 'discount': round(discount, 2),
                    'message': f'Coupon applied! You save ₹{discount:.2f}'})
