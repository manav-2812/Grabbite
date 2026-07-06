"""
Grabbite — API: Misc
/api/newsletter/subscribe, /api/footer/enquiry,
/api/orders/<id>/status   (order tracking)
"""
import os as _os
import json as _json

from flask import request, jsonify, current_app
from flask_login import current_user, login_required

from db import db
from models import Notification, Order
from blueprints.api import api_bp


# ─────────────────────────────────────────────────────────────────────────────
# NEWSLETTER / ENQUIRY
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route('/api/newsletter/subscribe', methods=['POST'])
def api_newsletter_subscribe():
    data  = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Please enter a valid email address.'}), 400
    sub_file = _os.path.join(current_app.root_path, 'newsletters.txt')
    try:
        existing = set()
        if _os.path.exists(sub_file):
            with open(sub_file, 'r') as f:
                existing = {line.strip() for line in f if line.strip()}
        if email in existing:
            return jsonify({'success': False, 'message': 'You are already subscribed! 🎉'})
        with open(sub_file, 'a') as f:
            f.write(email + '\n')
        if current_user.is_authenticated:
            db.session.add(Notification(
                user_id=current_user.id,
                title='Newsletter Subscribed! 📧',
                message="You're now subscribed to GrabBite deals and food updates. Stay tuned!",
                type='general',
            ))
            db.session.commit()
        return jsonify({'success': True, 'message': 'Subscribed! Welcome to the GrabBite family 🎉'})
    except Exception as e:
        current_app.logger.error(f'newsletter_subscribe error: {e}')
        return jsonify({'success': False, 'message': 'Subscription failed. Please try again.'}), 500


@api_bp.route('/api/footer/enquiry', methods=['POST'])
def api_footer_enquiry():
    data      = request.get_json() or {}
    form_type = data.get('form_type', 'unknown')
    email     = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'A valid email address is required.'}), 400
    enquiry_file = _os.path.join(current_app.root_path, 'enquiries.txt')
    try:
        with open(enquiry_file, 'a') as f:
            f.write(_json.dumps({'form': form_type, 'data': data}) + '\n')
    except Exception as e:
        current_app.logger.warning(f'enquiry log error: {e}')
    if current_user.is_authenticated and current_user.email == email:
        msg_map = {
            'partner-form': ('Restaurant Partnership Request Received 🤝',
                             'Thanks for applying to partner with GrabBite! Our team will contact you within 24–48 hours.'),
            'ride-form':    ('Delivery Partner Application Received 🏍️',
                             'Thanks for applying to ride with GrabBite! Our onboarding team will reach out shortly.'),
            'contact-form': ('We Got Your Message! 💬',
                             "Thanks for contacting GrabBite. We'll respond to your query within 24 hours."),
        }
        if form_type in msg_map:
            title, message = msg_map[form_type]
            db.session.add(Notification(user_id=current_user.id, title=title, message=message, type='general'))
            db.session.commit()
    return jsonify({'success': True, 'message': "Enquiry received! We'll be in touch within 24 hours."})


# ─────────────────────────────────────────────────────────────────────────────
# ORDER TRACKING API
# ─────────────────────────────────────────────────────────────────────────────

# Canonical pipeline order for the visual stepper
TRACKING_PIPELINE = ['placed', 'accepted', 'preparing', 'ready', 'on_the_way', 'delivered']

_STATUS_META = {
    'placed':     {'label': 'Order Placed',      'icon': 'fa-receipt',       'color': '#f59e0b'},
    'accepted':   {'label': 'Accepted',           'icon': 'fa-check-circle',  'color': '#3b82f6'},
    'preparing':  {'label': 'Preparing',          'icon': 'fa-fire-burner',   'color': '#8b5cf6'},
    'ready':      {'label': 'Ready for Pickup',   'icon': 'fa-bag-shopping',  'color': '#06b6d4'},
    'picked':     {'label': 'Picked Up',          'icon': 'fa-person-biking', 'color': '#10b981'},
    'on_the_way': {'label': 'Out for Delivery',   'icon': 'fa-motorcycle',    'color': '#10b981'},
    'delivered':  {'label': 'Delivered',          'icon': 'fa-circle-check',  'color': '#16a34a'},
    'cancelled':  {'label': 'Cancelled',          'icon': 'fa-circle-xmark',  'color': '#ef4444'},
}

_STATUS_DESCRIPTIONS = {
    'placed':     'Your order has been placed and is awaiting restaurant confirmation.',
    'accepted':   'The restaurant has accepted your order.',
    'preparing':  'Your food is being freshly prepared.',
    'ready':      'Your order is packed and ready for the delivery partner.',
    'picked':     'Your order has been picked up.',
    'on_the_way': 'Your order is on its way!',
    'delivered':  'Delivered! Enjoy your meal 🎉',
    'cancelled':  'This order has been cancelled.',
}


@api_bp.route('/api/orders/<int:order_id>/status')
@login_required
def api_order_status(order_id):
    """
    Return the current status, full status history, and pipeline progress
    for a specific order owned by the authenticated user.

    Used by the live tracking page to poll for updates and by the
    SocketIO client to sync after receiving a real_time_update event.
    """
    order = Order.query.filter_by(
        id=order_id, user_id=current_user.id
    ).first()

    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404

    status     = order.status
    is_done    = status in ('delivered', 'cancelled')
    pipeline   = TRACKING_PIPELINE

    # Which step is currently active in the pipeline (index)
    try:
        active_step = pipeline.index(status)
    except ValueError:
        # 'picked' maps visually to 'on_the_way' step
        active_step = pipeline.index('on_the_way') if status == 'picked' else 0

    history = [
        {
            'status':     h.status,
            'label':      _STATUS_META.get(h.status, {}).get('label', h.status.title()),
            'note':       h.note or '',
            'timestamp':  h.created_at.strftime('%d %b %Y, %I:%M %p') if h.created_at else '',
            'ts_iso':     h.created_at.isoformat() if h.created_at else '',
        }
        for h in order.status_history
    ]

    steps = [
        {
            'status':      s,
            'label':       _STATUS_META[s]['label'],
            'icon':        _STATUS_META[s]['icon'],
            'color':       _STATUS_META[s]['color'],
            'done':        pipeline.index(s) <= active_step,
            'active':      pipeline.index(s) == active_step,
        }
        for s in pipeline
    ]

    return jsonify({
        'success':       True,
        'order_id':      order.id,
        'status':        status,
        'status_label':  _STATUS_META.get(status, {}).get('label', status.title()),
        'status_desc':   _STATUS_DESCRIPTIONS.get(status, ''),
        'is_done':       is_done,
        'estimated_time': order.estimated_time,
        'restaurant_name': order.restaurant.name if order.restaurant else '',
        'total_amount':  float(order.total_amount),
        'payment_method': order.payment_method,
        'payment_status': order.payment_status,
        'delivered_at':  order.delivered_at.isoformat() if order.delivered_at else None,
        'created_at':    order.created_at.strftime('%d %b %Y, %I:%M %p') if order.created_at else '',
        'steps':         steps,
        'history':       history,
    })
