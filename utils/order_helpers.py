"""
Grabbite — utils/order_helpers.py
Plan 5 refactor: private order-building helpers extracted from blueprints/payment.py.

Provides:
  _build_order_from_cart    — validates cart and returns amounts / snapshot
  _create_order_record      — persists Order, Payment, OrderStatusHistory, CouponUsage
  _post_order_notifications — fires admin + user notifications after commit
"""
from flask import url_for, current_app
from flask_login import current_user

from db import db
from models import (Cart, FoodItem, Restaurant, Offer, CouponUsage,
                    Order, Payment, OrderStatusHistory, OrderItem,
                    Notification, AdminNotification)


# ─────────────────────────────────────────────────────────────────────────────
# BUILD ORDER FROM CART
# ─────────────────────────────────────────────────────────────────────────────

def _build_order_from_cart(data):
    """Validate cart and build order totals.

    Returns (cart_rows, amounts_dict, restaurant_id, items_snapshot) or raises ValueError.
    """
    cart_rows = (
        db.session.query(Cart, FoodItem, Restaurant)
        .join(FoodItem, Cart.food_item_id == FoodItem.id)
        .join(Restaurant, FoodItem.restaurant_id == Restaurant.id)
        .filter(Cart.user_id == current_user.id)
        .all()
    )

    if not cart_rows:
        raise ValueError('Your cart is empty')

    subtotal     = sum(c.quantity * f.price for c, f, _ in cart_rows)
    tax          = round(subtotal * 0.18, 2)
    delivery_fee = 0.0 if subtotal > 500 else 40.0
    coupon_code  = str(data.get('coupon_code') or '').strip().upper()
    discount     = 0.0

    if coupon_code:
        offer = Offer.query.filter_by(code=coupon_code).first()
        if offer:
            valid, msg = offer.is_valid()
            if valid and subtotal >= offer.min_order_amount:
                already = CouponUsage.query.filter_by(
                    offer_id=offer.id, user_id=current_user.id
                ).first()
                if not already:
                    if offer.discount_type == 'percentage':
                        raw      = subtotal * offer.discount_value / 100
                        discount = min(raw, offer.max_discount) if offer.max_discount else raw
                    else:
                        discount = min(offer.discount_value, subtotal)
                    discount = round(discount, 2)

    platform_fee  = 5.0
    final_total   = round(subtotal + tax + delivery_fee - discount + platform_fee, 2)
    restaurant_id = cart_rows[0][2].id

    items_snapshot = [
        {
            'id':              f.id,
            'name':            f.name,
            'restaurant_name': r.name,
            'quantity':        c.quantity,
            'price':           float(f.price),
            'total':           float(c.quantity * f.price),
        }
        for c, f, r in cart_rows
    ]

    amounts = {
        'subtotal':    subtotal,
        'tax':         tax,
        'delivery_fee': delivery_fee,
        'discount':    discount,
        'platform_fee': platform_fee,
        'total':       final_total,
        'coupon_code': coupon_code or None,
    }
    return cart_rows, amounts, restaurant_id, items_snapshot


# ─────────────────────────────────────────────────────────────────────────────
# CREATE ORDER RECORD
# ─────────────────────────────────────────────────────────────────────────────

def _create_order_record(data, amounts, restaurant_id, items_snapshot, payment_method,
                         payment_status='pending', gateway_order_id=None):
    """Persist Order + Payment record, history entry, coupon usage.

    Does NOT commit — caller is responsible for db.session.commit().
    Returns (order, payment_rec).
    """
    delivery_location = data.get('delivery_location') or {}
    location_note = ''
    if isinstance(delivery_location, dict):
        parts = [
            str(delivery_location.get(k) or '').strip()
            for k in ('name', 'city', 'state')
            if str(delivery_location.get(k) or '').strip()
        ]
        if parts:
            location_note = 'Location: ' + ', '.join(dict.fromkeys(parts))

    order_notes = str(data.get('notes') or '').strip()[:1000]
    if location_note:
        order_notes = f'{order_notes}\n{location_note}'.strip()[:1000]

    delivery_address = str(data.get('delivery_address') or '').strip()[:500]
    if len(delivery_address) < 5:
        raise ValueError('Delivery address looks too short.')

    order = Order(
        user_id=current_user.id,
        restaurant_id=restaurant_id,
        order_items=items_snapshot,
        subtotal=amounts['subtotal'],
        tax=amounts['tax'],
        delivery_fee=amounts['delivery_fee'],
        discount=amounts['discount'],
        total_amount=amounts['total'],
        delivery_address=delivery_address,
        delivery_phone=data.get('delivery_phone', ''),
        payment_method=payment_method,
        payment_status=payment_status,
        coupon_code=amounts.get('coupon_code'),
        status='placed',
        notes=order_notes,
    )
    if gateway_order_id:
        order.razorpay_order_id = gateway_order_id

    db.session.add(order)
    db.session.flush()  # get order.id before adding child rows

    for item in items_snapshot:
        db.session.add(OrderItem(
            order_id=order.id,
            food_item_id=item.get('id'),
            name=item['name'],
            price=float(item['price']),
            quantity=int(item['quantity']),
            image=item.get('image'),
        ))

    payment_rec = Payment(
        order_id=order.id,
        user_id=current_user.id,
        amount=amounts['total'],
        payment_method=payment_method,
        status=payment_status,
        gateway_order_id=gateway_order_id,
    )
    db.session.add(payment_rec)

    db.session.add(OrderStatusHistory(
        order_id=order.id, status='placed', note='Order placed by customer'
    ))

    # Coupon usage — uses atomic UPDATE to avoid race conditions
    coupon_code = amounts.get('coupon_code')
    if coupon_code and amounts.get('discount', 0) > 0:
        offer = Offer.query.filter_by(code=coupon_code).first()
        if offer and not CouponUsage.query.filter_by(
            offer_id=offer.id, user_id=current_user.id
        ).first():
            db.session.add(CouponUsage(
                offer_id=offer.id, user_id=current_user.id, order_id=order.id,
            ))
            from sqlalchemy import update as _sa_update
            res = db.session.execute(
                _sa_update(Offer)
                .where(
                    db.and_(
                        Offer.id == offer.id,
                        db.or_(
                            Offer.usage_limit.is_(None),
                            Offer.used_count < Offer.usage_limit,
                        ),
                    )
                )
                .values(used_count=Offer.used_count + 1)
            )
            if res.rowcount == 0:
                current_app.logger.warning(
                    f'Offer {offer.code} usage_limit reached during order commit; '
                    f'reverting discount on order {order.id}'
                )
                order.discount     = 0.0
                order.total_amount = round(
                    order.subtotal + order.tax + order.delivery_fee + 5.0, 2
                )
                payment_rec.amount = order.total_amount

    return order, payment_rec


# ─────────────────────────────────────────────────────────────────────────────
# POST-ORDER NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

def _post_order_notifications(order, amounts):
    """Fire admin + user notifications and trigger order-confirmation email.

    Commits to the DB before sending the email thread.
    """
    db.session.add(AdminNotification(
        title='New Order',
        message=f'Order #{order.id} placed by {current_user.name} — ₹{amounts["total"]}',
        type='order',
    ))
    db.session.add(Notification(
        user_id=current_user.id,
        title='Order Placed! 🎉',
        message=f'Your order #{order.id} is confirmed. Total: ₹{amounts["total"]}',
        type='order_update',
        link=url_for('account.orders'),
    ))
    db.session.commit()

    try:
        from utils.mail import send_order_confirmation
        import threading
        _user = current_user._get_current_object()
        threading.Thread(
            target=send_order_confirmation,
            args=(_user, order),
            daemon=True,
        ).start()
    except Exception as _me:
        current_app.logger.warning(f'Order confirmation email failed to start: {_me}')
