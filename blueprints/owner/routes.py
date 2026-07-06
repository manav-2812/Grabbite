"""
Grabbite — Restaurant Owner Blueprint
Provides the full restaurant owner dashboard:
  /owner/dashboard   — stats overview
  /owner/dishes      — manage dishes (list/add/edit/delete)
  /owner/orders      — view & manage incoming orders
  /owner/profile     — edit restaurant profile
"""
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, jsonify, abort,
)
from flask_login import login_required, current_user
from sqlalchemy import func
from db import db
from models import (
    Restaurant, FoodItem, Order, OrderStatusHistory,
    Notification, AdminNotification,
)
from utils.decorators import owner_required
from datetime import datetime, timezone, timedelta
import os
from werkzeug.utils import secure_filename

owner_bp = Blueprint('owner', __name__, url_prefix='/owner')

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_owner_restaurant():
    """Return the restaurant owned by the current user, or abort 403."""
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not restaurant and current_user.is_administrator():
        # Admins can access /owner/* for any restaurant via ?restaurant_id=
        rid = request.args.get('restaurant_id', type=int)
        if rid:
            restaurant = Restaurant.query.get_or_404(rid)
    if not restaurant:
        abort(403)
    return restaurant


ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}


def _allowed_image(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# ── Dashboard ─────────────────────────────────────────────────────────────────

@owner_bp.route('/dashboard')
@login_required
@owner_required
def dashboard():
    restaurant = _get_owner_restaurant()
    now        = datetime.now(timezone.utc)
    week_ago   = now - timedelta(days=7)

    total_orders    = Order.query.filter_by(restaurant_id=restaurant.id).count()
    pending_orders  = Order.query.filter_by(
        restaurant_id=restaurant.id, status='placed'
    ).count()
    today_orders    = Order.query.filter(
        Order.restaurant_id == restaurant.id,
        func.date(Order.created_at) == func.date(now)
    ).count()
    week_revenue    = db.session.query(func.sum(Order.total_amount)).filter(
        Order.restaurant_id == restaurant.id,
        Order.payment_status == 'paid',
        Order.created_at >= week_ago,
    ).scalar() or 0.0

    top_dishes = db.session.query(
        FoodItem.name, func.sum(Order.total_amount).label('revenue')
    ).join(Order, Order.restaurant_id == restaurant.id)\
     .filter(FoodItem.restaurant_id == restaurant.id)\
     .group_by(FoodItem.id)\
     .order_by(func.sum(Order.total_amount).desc())\
     .limit(5).all()

    recent_orders = Order.query.filter_by(restaurant_id=restaurant.id)\
        .order_by(Order.created_at.desc()).limit(10).all()

    return render_template('owner/dashboard.html',
        restaurant=restaurant,
        total_orders=total_orders,
        pending_orders=pending_orders,
        today_orders=today_orders,
        week_revenue=week_revenue,
        top_dishes=top_dishes,
        recent_orders=recent_orders,
    )


# ── Dishes ────────────────────────────────────────────────────────────────────

@owner_bp.route('/dishes')
@login_required
@owner_required
def dishes():
    restaurant = _get_owner_restaurant()
    page       = request.args.get('page', 1, type=int)
    query      = FoodItem.query.filter_by(restaurant_id=restaurant.id)
    category   = request.args.get('category', '').strip()
    if category:
        query = query.filter_by(category=category)
    dishes_pg  = query.order_by(FoodItem.category, FoodItem.name).paginate(
        page=page, per_page=30, error_out=False
    )
    categories = db.session.query(FoodItem.category)\
        .filter_by(restaurant_id=restaurant.id)\
        .distinct().all()
    return render_template('owner/dishes.html',
        restaurant=restaurant,
        dishes=dishes_pg,
        categories=[c[0] for c in categories if c[0]],
        current_category=category,
    )


@owner_bp.route('/dishes/add', methods=['GET', 'POST'])
@login_required
@owner_required
def add_dish():
    restaurant = _get_owner_restaurant()
    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        price        = float(request.form.get('price', 0))
        description  = request.form.get('description', '').strip()
        category     = request.form.get('category', '').strip()
        is_veg       = request.form.get('is_vegetarian') == 'on'
        is_bestseller= request.form.get('is_bestseller') == 'on'
        is_available = request.form.get('is_available', 'on') == 'on'

        if not name or price <= 0:
            flash('Name and a positive price are required.', 'error')
            return render_template('owner/dish_form.html', restaurant=restaurant, dish=None)

        image_filename = ''
        file = request.files.get('image')
        if file and file.filename and _allowed_image(file.filename):
            from flask import current_app
            filename = secure_filename(file.filename)
            assert current_app.static_folder is not None
            upload_path = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            image_filename = filename

        dish = FoodItem(
            restaurant_id=restaurant.id,
            name=name,
            price=price,
            description=description,
            category=category,
            image=image_filename,
            is_vegetarian=is_veg,
            is_bestseller=is_bestseller,
            is_available=is_available,
        )
        db.session.add(dish)
        db.session.commit()
        flash(f'"{name}" added successfully!', 'success')
        return redirect(url_for('owner.dishes'))

    return render_template('owner/dish_form.html', restaurant=restaurant, dish=None)


@owner_bp.route('/dishes/edit/<int:dish_id>', methods=['GET', 'POST'])
@login_required
@owner_required
def edit_dish(dish_id):
    restaurant = _get_owner_restaurant()
    dish = FoodItem.query.filter_by(id=dish_id, restaurant_id=restaurant.id).first_or_404()

    if request.method == 'POST':
        dish.name         = request.form.get('name', dish.name).strip()
        dish.price        = float(request.form.get('price', dish.price))
        dish.description  = request.form.get('description', '').strip()
        dish.category     = request.form.get('category', '').strip()
        dish.is_vegetarian= request.form.get('is_vegetarian') == 'on'
        dish.is_bestseller= request.form.get('is_bestseller') == 'on'
        dish.is_available = request.form.get('is_available', 'on') == 'on'

        file = request.files.get('image')
        if file and file.filename and _allowed_image(file.filename):
            from flask import current_app
            filename = secure_filename(file.filename)
            assert current_app.static_folder is not None
            upload_path = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            dish.image = filename

        db.session.commit()
        flash('Dish updated!', 'success')
        return redirect(url_for('owner.dishes'))

    return render_template('owner/dish_form.html', restaurant=restaurant, dish=dish)


@owner_bp.route('/dishes/delete/<int:dish_id>', methods=['POST'])
@login_required
@owner_required
def delete_dish(dish_id):
    restaurant = _get_owner_restaurant()
    dish = FoodItem.query.filter_by(id=dish_id, restaurant_id=restaurant.id).first_or_404()
    db.session.delete(dish)
    db.session.commit()
    flash(f'"{dish.name}" deleted.', 'success')
    return redirect(url_for('owner.dishes'))


# ── Orders ────────────────────────────────────────────────────────────────────

@owner_bp.route('/orders')
@login_required
@owner_required
def orders():
    restaurant = _get_owner_restaurant()
    status_filter = request.args.get('status', '')
    page          = request.args.get('page', 1, type=int)

    query = Order.query.filter_by(restaurant_id=restaurant.id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    orders_pg = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('owner/orders.html',
        restaurant=restaurant,
        orders=orders_pg,
        status_filter=status_filter,
    )


@owner_bp.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
@owner_required
def update_order_status(order_id):
    restaurant = _get_owner_restaurant()
    order = Order.query.filter_by(id=order_id, restaurant_id=restaurant.id).first_or_404()
    new_status = request.form.get('status', '').strip()

    valid = ('placed', 'accepted', 'preparing', 'ready', 'picked',
             'on_the_way', 'delivered', 'cancelled')
    if new_status not in valid:
        flash('Invalid status.', 'error')
        return redirect(url_for('owner.orders'))

    order.status = new_status
    # H8 fix: stamp the delivery timestamp when the order is marked delivered
    # so analytics/delivery-time reports can be accurate.
    if new_status == 'delivered' and not order.delivered_at:
        from datetime import datetime, timezone
        order.delivered_at = datetime.now(timezone.utc)
    db.session.add(OrderStatusHistory(
        order_id=order.id,
        status=new_status,
        note=f'Status updated by restaurant owner',
    ))

    # Notify customer
    status_messages = {
        'accepted':   ('Order Accepted! 🎉', f'Restaurant accepted your order #{order.id}.'),
        'preparing':  ('Preparing your food 🍳', f'Order #{order.id} is being prepared.'),
        'ready':      ('Order Ready! ✅', f'Order #{order.id} is ready for pickup.'),
        'on_the_way': ('Out for delivery! 🛵', f'Order #{order.id} is on the way.'),
        'delivered':  ('Delivered! 🎊', f'Order #{order.id} has been delivered. Enjoy!'),
        'cancelled':  ('Order Cancelled ❌', f'Order #{order.id} was cancelled by the restaurant.'),
    }
    if new_status in status_messages:
        title, message = status_messages[new_status]
        db.session.add(Notification(
            user_id=order.user_id,
            title=title,
            message=message,
            type='order_update',
            link=url_for('account.orders'),
        ))

    db.session.commit()
    flash(f'Order #{order.id} marked as {new_status}.', 'success')

    # Broadcast real-time status update to the customer via WebSocket
    try:
        from app import broadcast_update
        broadcast_update('order_update', {
            'order_id':   order.id,
            'status':     new_status,
            'message':    status_messages.get(new_status, ('', ''))[1],
        }, room='authenticated_users')
    except Exception:
        pass  # WebSocket failure must never break order management

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'status': new_status})
    return redirect(url_for('owner.orders'))


# ── Restaurant Profile ────────────────────────────────────────────────────────

@owner_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@owner_required
def profile():
    restaurant = _get_owner_restaurant()

    if request.method == 'POST':
        restaurant.name          = request.form.get('name', restaurant.name).strip()
        restaurant.description   = request.form.get('description', '').strip()
        restaurant.phone         = request.form.get('phone', '').strip()
        restaurant.address       = request.form.get('address', '').strip()
        restaurant.cuisine_type  = request.form.get('cuisine_type', '').strip()
        restaurant.opening_time  = request.form.get('opening_time', '').strip()
        restaurant.closing_time  = request.form.get('closing_time', '').strip()
        restaurant.delivery_time = request.form.get('delivery_time', type=int) or restaurant.delivery_time
        restaurant.min_order     = request.form.get('min_order', type=float) or restaurant.min_order

        file = request.files.get('image')
        if file and file.filename and _allowed_image(file.filename):
            from flask import current_app
            filename = secure_filename(file.filename)
            assert current_app.static_folder is not None
            upload_path = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            restaurant.image = filename

        db.session.commit()
        flash('Restaurant profile updated!', 'success')
        return redirect(url_for('owner.profile'))

    return render_template('owner/profile.html', restaurant=restaurant)
