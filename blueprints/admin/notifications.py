"""
Grabbite — Admin: Notifications
/admin/notifications, /admin/notifications/send
"""
from datetime import datetime, timezone

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from db import db
from models import User, Order, Notification, AdminNotification
from blueprints.admin import admin, log_admin_activity
from utils.decorators import admin_required


@admin.route('/notifications')
@login_required
@admin_required
def admin_notifications():
    notif_list = AdminNotification.query.order_by(
        AdminNotification.created_at.desc()
    ).all()
    return render_template('admin/notifications.html', notifications=notif_list)


@admin.route('/notifications/send', methods=['POST'])
@login_required
@admin_required
def send_notification():
    try:
        title        = request.form.get('title')
        message      = request.form.get('message')
        notif_type   = request.form.get('type', 'general')
        target_users = request.form.get('target_users', 'all')

        admin_notif = AdminNotification(
            title=title,
            message=message,
            type=notif_type,
            target_users=target_users,
            is_sent=True,
            sent_at=datetime.now(timezone.utc),
        )
        db.session.add(admin_notif)

        if target_users == 'all':
            user_list = User.query.filter_by(is_active=True).all()
        elif target_users == 'active_orders':
            user_list = User.query.join(Order).filter(
                Order.status.in_(['placed', 'accepted', 'preparing'])
            ).distinct().all()
        else:
            ids       = [int(x) for x in target_users.split(',') if x.strip().isdigit()]
            user_list = User.query.filter(User.id.in_(ids)).all()

        for u in user_list:
            notif = Notification(
                user_id=u.id, title=title,
                message=message, type=notif_type,
            )
            db.session.add(notif)

        db.session.commit()
        log_admin_activity('Sent Notification', 'notification', admin_notif.id,
                           f'Sent to {len(user_list)} users')
        flash(f'Notification sent to {len(user_list)} users!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('admin.admin_notifications'))
