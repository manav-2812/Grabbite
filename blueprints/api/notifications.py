"""
Grabbite — API: Notifications
/api/notifications, /api/notifications/read, /api/notifications/read-all,
/api/notifications/seed
"""
from flask import request, jsonify
from flask_login import current_user, login_required

from db import db
from models import Notification
from blueprints.api import api_bp


@api_bp.route('/api/notifications')
@login_required
def api_get_notifications():
    """Return the current user's notifications (newest first, max 30)."""
    unread_only = request.args.get('unread_only', '0') == '1'
    query = Notification.query.filter_by(user_id=current_user.id)
    if unread_only:
        query = query.filter_by(is_read=False)
    notifs = query.order_by(Notification.created_at.desc()).limit(30).all()
    unread_count = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()
    return jsonify({
        'success':       True,
        'unread_count':  unread_count,
        'notifications': [{
            'id':         n.id,
            'title':      n.title,
            'message':    n.message,
            'type':       n.type or 'general',
            'link':       n.link,
            'is_read':    n.is_read,
            'created_at': n.created_at.isoformat() if n.created_at else '',
        } for n in notifs],
    })


@api_bp.route('/api/notifications/read', methods=['POST'])
@login_required
def api_mark_notification_read():
    data = request.get_json() or {}
    nid  = data.get('id')
    if nid:
        Notification.query.filter_by(
            id=nid, user_id=current_user.id
        ).update({'is_read': True})
        db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/api/notifications/seed', methods=['POST'])
@login_required
def api_seed_notifications():
    seeds = [
        {'title': '🎉 Welcome to GrabBite!',
         'message': 'Thanks for joining! Explore restaurants near you and enjoy your first order.',
         'type': 'general', 'link': '/restaurants'},
        {'title': '🏷️ Special Offer: 20% OFF',
         'message': 'Use code GRAB20 on your next order to get 20% off (max ₹200 discount).',
         'type': 'promo', 'link': '/restaurants'},
        {'title': '📦 Order Delivered Successfully',
         'message': 'Your last order has been delivered. Rate your experience and earn reward points!',
         'type': 'order', 'link': '/orders'},
    ]
    added = 0
    for s in seeds:
        exists = Notification.query.filter_by(
            user_id=current_user.id, title=s['title']
        ).first()
        if not exists:
            db.session.add(Notification(user_id=current_user.id, **s))
            added += 1
    db.session.commit()
    return jsonify({'success': True, 'added': added})
