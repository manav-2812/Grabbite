"""
Grabbite — Admin: User Management
/admin/users, /admin/api/user/*
"""
from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from db import db
from models import User, Order, Review
from blueprints.admin import admin, log_admin_activity
from utils.decorators import admin_required


@admin.route('/users')
@login_required
@admin_required
def users():
    page   = request.args.get('page', 1, type=int)
    q      = request.args.get('q', '')
    role_f = request.args.get('role', '')

    query = User.query
    if q:
        query = query.filter(db.or_(
            User.name.ilike(f'%{q}%'),
            User.email.ilike(f'%{q}%'),
        ))
    if role_f:
        query = query.filter(User.role == role_f)

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template('admin/users.html',
                           users=pagination.items,
                           pagination=pagination,
                           q=q, role_f=role_f)


@admin.route('/api/user/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def get_user_details(user_id):
    try:
        u           = User.query.get_or_404(user_id)
        orders      = Order.query.filter_by(user_id=user_id).all()
        total_spent = sum(o.total_amount for o in orders if o.total_amount)
        reviews     = Review.query.filter_by(user_id=user_id).all()
        avg_rating  = sum(r.rating for r in reviews) / len(reviews) if reviews else 0

        return jsonify({
            'success': True,
            'user': {
                'id':               u.id,
                'name':             u.name,
                'email':            u.email,
                'contact':          u.contact,
                'address':          u.address,
                'profile_photo':    u.profile_photo,
                'is_active':        u.is_active,
                'role':             u.role,
                'created_at':       u.created_at.isoformat() if u.created_at else None,
                'is_administrator': u.is_administrator(),
            },
            'stats': {
                'orders':      len(orders),
                'total_spent': total_spent,
                'reviews':     len(reviews),
                'avg_rating':  round(avg_rating, 1),
            },
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/user/toggle-status', methods=['POST'])
@login_required
@admin_required
def update_user_status():
    data      = request.get_json() or {}
    user_id   = data.get('user_id')
    is_active = data.get('is_active')

    if user_id is None or is_active is None:
        return jsonify({'success': False, 'message': 'user_id and is_active required'}), 400

    u = User.query.get_or_404(user_id)
    if u.is_administrator():
        return jsonify({'success': False, 'message': 'Cannot modify admin status'}), 403

    u.is_active = bool(is_active)
    db.session.commit()
    log_admin_activity('Toggled User Status', 'user', user_id)
    return jsonify({'success': True, 'message': 'User status updated'})


@admin.route('/api/user/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    """Change a user's role. Prevents self-demotion."""
    data     = request.get_json() or {}
    new_role = data.get('role', '').strip()
    valid_roles = ('customer', 'restaurant_owner', 'admin', 'delivery_partner')
    if new_role not in valid_roles:
        return jsonify({'success': False, 'message': f'Invalid role. Must be one of: {valid_roles}'}), 400

    u = User.query.get_or_404(user_id)
    if u.id == current_user.id and new_role != 'admin':
        return jsonify({'success': False, 'message': 'Cannot remove your own admin role.'}), 403

    old_role = u.role
    u.role = new_role
    if new_role == 'admin':
        u.is_admin = True
    elif old_role == 'admin':
        u.is_admin = False

    db.session.commit()
    log_admin_activity('Changed User Role', 'user', user_id, f'{old_role} -> {new_role}')
    return jsonify({'success': True, 'message': f'Role updated to {new_role}'})


@admin.route('/api/user/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Hard-delete a user. Prevents self-deletion and last-admin deletion."""
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete your own account.'}), 403
    u = User.query.get_or_404(user_id)
    if (u.role == 'admin' or u.is_admin) and User.query.filter(
        db.or_(User.role == 'admin', User.is_admin.is_(True))
    ).count() <= 1:
        return jsonify({
            'success': False,
            'message': 'Cannot delete the last administrator account.'
        }), 400
    name = u.name
    db.session.delete(u)
    db.session.commit()
    log_admin_activity('Deleted User', 'user', user_id, f'Deleted: {name}')
    return jsonify({'success': True, 'message': f'User "{name}" deleted.'})
