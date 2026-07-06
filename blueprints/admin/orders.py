"""
Grabbite — Admin: Order Management
/admin/orders, /admin/api/order/*, /admin/api/update-order-status
"""
from datetime import datetime, timezone

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from db import db
from models import Order, OrderStatusHistory, Notification
from blueprints.admin import admin, broadcast_update, log_admin_activity
from utils.decorators import admin_required


@admin.route('/orders')
@login_required
@admin_required
def orders():
    page     = request.args.get('page', 1, type=int)
    status_f = request.args.get('status', '')
    query    = Order.query
    if status_f:
        query = query.filter(Order.status == status_f)
    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/orders.html',
                           orders=pagination.items,
                           pagination=pagination,
                           status_f=status_f)


@admin.route('/api/order/<int:order_id>', methods=['GET'])
@login_required
@admin_required
def get_order_details(order_id):
    o = Order.query.get_or_404(order_id)
    return jsonify({
        'id':               o.id,
        'status':           o.status,
        'payment_status':   o.payment_status,
        'total_amount':     o.total_amount,
        'delivery_address': o.delivery_address,
        'delivery_phone':   o.delivery_phone,
        'created_at':       o.created_at.isoformat(),
        'items':            o.order_items or [],
        'user': {
            'name':    o.user.name,
            'email':   o.user.email,
            'contact': o.user.contact,
        },
    })


@admin.route('/api/update-order-status', methods=['POST'])
@login_required
@admin_required
def update_order_status():
    data       = request.get_json() or {}
    order_id   = data.get('order_id')
    new_status = data.get('status')

    if not order_id or not new_status:
        return jsonify({'success': False, 'message': 'order_id and status required'}), 400

    try:
        order            = Order.query.get_or_404(order_id)
        order.status     = new_status
        order.updated_at = datetime.now(timezone.utc)
        if new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = datetime.now(timezone.utc)

        history = OrderStatusHistory(
            order_id=order_id, status=new_status,
            note=f'Status changed by admin {current_user.name}',
        )
        db.session.add(history)

        notif = Notification(
            user_id=order.user_id,
            title='Order Status Update',
            message=f'Your order #{order.id} is now: {new_status.replace("_", " ").title()}',
            type='order_update',
        )
        db.session.add(notif)
        db.session.commit()

        broadcast_update('order_status_changed', {
            'order_id': order_id, 'status': new_status
        }, room='admin_users')

        return jsonify({'success': True, 'message': 'Order status updated'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/order/<int:order_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        db.session.delete(order)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Order deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
