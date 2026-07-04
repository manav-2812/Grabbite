"""
Grabbite — Admin Blueprint
All admin-only routes for managing restaurants, dishes, blogs, users, orders,
offers, notifications, payments, analytics, and the database viewer.

FIXES APPLIED:
- Added 'import secrets' (was missing, caused add-dish crash)
- Fixed current_user.username → current_user.name for Blog.author
- Fixed Blog fields: added slug, status, featured to model (done in models.py)
- Fixed FoodItem dietary flags (added to model in models.py)
- Fixed Restaurant.is_active (added to model in models.py)
- Fixed nested transaction issue in DELETE restaurant
- Fixed duplicate route prefixes (/admin/admin/...) → /admin/...
- Fixed Order.total_price → Order.total_amount
- Fixed Order.order_status → Order.status
- Fixed add_blog to use current_user.name instead of current_user.username
- Fixed Offer.valid_from → Offer.start_date, Offer.valid_until → Offer.end_date
- Fixed AdminNotification: removed 'sent_by' (not in model)
- Fixed send_notification: uses Order.status not Order.order_status
- Fixed get_user_details: uses order.total_amount not order.total_price
- Fixed get_user_details: uses user.profile_photo not user.profile_picture
- Added missing database_viewer route
"""
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, current_app)
from flask_login import login_required, current_user
from functools import wraps
from models import (User, Restaurant, FoodItem, Order, OrderStatusHistory,
                    Blog, Review, Notification, AdminActivity, AdminNotification,
                    Offer, Payment, SupportTicket, Cart)
from db import db
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
import os
import uuid
import secrets   # ← was missing, caused add-dish crash
import json

# HIGH-6 fix: import the shared decorators instead of re-implementing them here.
from utils.decorators import admin_required, owner_required  # noqa: F401

admin = Blueprint('admin', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def broadcast_update(event_type, data, room='authenticated_users'):
    """Broadcast real-time updates — wrapped so failure doesn't crash the app."""
    try:
        from app import socketio
        socketio.emit('real_time_update', {
            'type':      event_type,
            'data':      data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, room=room)  # type: ignore[call-arg]
    except Exception as exc:
        # LOW-3: log at DEBUG — SocketIO emit failures are non-fatal but useful for troubleshooting
        current_app.logger.debug(f'broadcast_update({event_type}) skipped: {exc}')


def log_admin_activity(action, target_type, target_id=None, details=None):
    """Log admin activity to the activity table."""
    try:
        activity = AdminActivity(
            admin_id=current_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=request.remote_addr,
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        current_app.logger.warning(f'log_admin_activity failed: {e}')


def allowed_file(filename: str) -> bool:
    ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


# H11 fix: enforce that the uploaded file's actual MIME content matches the
# extension. The standard extension check is bypassable (rename evil.exe to
# evil.jpg) so we additionally inspect the first ~12 bytes (magic numbers)
# for the most common image types.
_IMAGE_MAGIC = (
    b'\xff\xd8\xff',                       # JPEG
    b'\x89PNG\r\n\x1a\n',                  # PNG
    b'GIF87a', b'GIF89a',                   # GIF
    b'RIFF',                                # WEBP (RIFF....WEBP)
)


def _looks_like_image(file_storage) -> bool:
    """Read the leading bytes from the upload and check for a known image
    magic signature. Returns True if the file's content matches an image
    type we accept."""
    try:
        head = file_storage.stream.read(12)
    except Exception:
        return False
    finally:
        try:
            file_storage.stream.seek(0)
        except Exception:
            pass  # stream seek failure is non-fatal; already read 0 bytes
    if not head:
        return False
    for sig in _IMAGE_MAGIC:
        if head.startswith(sig):
            # For WEBP we also want the WEBP marker in the first 12 bytes.
            if sig == b'RIFF' and b'WEBP' not in head[:12]:
                continue
            return True
    return False


def save_image(file, old_image=None) -> tuple:
    """Save an uploaded image and optionally remove the old one.
    Returns (filename, error_msg). On success error_msg is None."""
    if not file or file.filename == '':
        return None, 'No file selected'
    if not allowed_file(file.filename):
        return None, 'Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP'
    # H11 fix: verify the actual file content matches an image signature.
    if not _looks_like_image(file):
        return None, 'File content does not match an allowed image format.'
    try:
        ext           = file.filename.rsplit('.', 1)[1].lower()
        unique_name   = f'{uuid.uuid4().hex}.{ext}'
        filepath      = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
        file.save(filepath)

        # Remove old file if it exists and is not a default image
        if old_image and not old_image.endswith('_default.jpg') and \
                old_image not in ('default.jpg', 'blog_default.jpg',
                                  'restaurant_default.jpg', 'food_default.jpg'):
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_image)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass

        return unique_name, None
    except Exception as e:
        return None, str(e)

# Legacy alias used by some routes
handle_image_upload = save_image


# HIGH-6 fix: admin_required is now imported from utils.decorators at the top.
# Old local definition removed to avoid a duplicate-name shadow.


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_users       = User.query.count()
    total_restaurants = Restaurant.query.count()
    total_dishes      = FoodItem.query.count()
    total_blogs       = Blog.query.count()
    total_orders      = Order.query.count()
    active_offers     = Offer.query.filter_by(is_active=True).count()

    # Revenue (sum of delivered orders)
    revenue_result = db.session.query(db.func.sum(Order.total_amount))\
        .filter(Order.status == 'delivered').scalar()
    total_revenue = float(revenue_result or 0)

    recent_activities = AdminActivity.query.order_by(
        AdminActivity.created_at.desc()
    ).limit(10).all()

    # MED-15: joinedload prevents N+1 when the template accesses order.user / order.restaurant
    from sqlalchemy.orm import joinedload as _joinedload
    recent_orders = (
        Order.query
        .options(
            _joinedload(Order.user),
            _joinedload(Order.restaurant),
        )
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    # 7-day sales trend
    today = datetime.now(timezone.utc).date()
    daily_sales = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        amt = db.session.query(db.func.sum(Order.total_amount))\
            .filter(db.func.date(Order.created_at) == day).scalar() or 0
        daily_sales.append({'date': day.strftime('%a'), 'amount': float(amt)})

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_restaurants=total_restaurants,
                           total_dishes=total_dishes,
                           total_blogs=total_blogs,
                           total_orders=total_orders,
                           active_offers=active_offers,
                           total_revenue=total_revenue,
                           recent_activities=recent_activities,
                           recent_orders=recent_orders,
                           daily_sales=daily_sales)


# ─────────────────────────────────────────────────────────────────────────────
# STATS APIS
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/api/stats/restaurants')
@login_required
@admin_required
def api_stats_restaurants():
    return jsonify({'count': Restaurant.query.count()})


@admin.route('/api/stats/dishes')
@login_required
@admin_required
def api_stats_dishes():
    return jsonify({'count': FoodItem.query.count()})


@admin.route('/api/stats/blogs')
@login_required
@admin_required
def api_stats_blogs():
    return jsonify({'count': Blog.query.count()})


@admin.route('/api/stats/users')
@login_required
@admin_required
def api_stats_users():
    return jsonify({'count': User.query.count()})


@admin.route('/api/stats/orders')
@login_required
@admin_required
def api_stats_orders():
    return jsonify({'count': Order.query.count()})


@admin.route('/api/stats/offers')
@login_required
@admin_required
def api_stats_offers():
    return jsonify({'count': Offer.query.filter_by(is_active=True).count()})


@admin.route('/api/analytics')
@login_required
@admin_required
def get_analytics():
    """Analytics payload shaped for templates/admin/dashboard.html chart init."""
    try:
        today      = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=6)

        daily_orders = []
        daily_revenue = []
        for i in range(7):
            day = start_date + timedelta(days=i)
            label = day.strftime('%a')
            cnt = Order.query.filter(db.func.date(Order.created_at) == day).count()
            rev = db.session.query(
                db.func.coalesce(db.func.sum(Order.total_amount), 0)
            ).filter(db.func.date(Order.created_at) == day).scalar()
            daily_orders.append({'date': label, 'count': cnt})
            daily_revenue.append({'date': label, 'revenue': float(rev or 0)})

        top_restaurants = [
            {'name': name, 'order_count': cnt}
            for name, cnt in (
                db.session.query(Restaurant.name, db.func.count(Order.id))
                .outerjoin(Order, Order.restaurant_id == Restaurant.id)
                .group_by(Restaurant.id)
                .order_by(db.func.count(Order.id).desc())
                .limit(5)
                .all()
            )
        ]

        customer_count = User.query.filter(User.role == 'customer').count()
        owner_count    = User.query.filter(User.role == 'restaurant_owner').count()
        admin_count    = User.query.filter(
            db.or_(User.is_admin.is_(True), User.role == 'admin')
        ).count()

        return jsonify({
            'daily_orders':     daily_orders,
            'daily_revenue':    daily_revenue,
            'top_restaurants':  top_restaurants,
            'customer_count':   customer_count,
            'owner_count':      owner_count,
            'admin_count':      admin_count,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE VIEWER
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/database')
@login_required
@admin_required
def database_viewer():
    """Admin database viewer — supports table selection and pagination."""
    import sqlalchemy as sa

    PER_PAGE = 50

    # Map of display key → SQLAlchemy model  (no hardcoded table-name string needed)
    MODEL_MAP = {
        'users':         User,
        'restaurants':   Restaurant,
        'food_items':    FoodItem,
        'orders':        Order,
        'cart':          Cart,
        'blogs':         Blog,
        'reviews':       Review,
        'offers':        Offer,
        'payments':      Payment,
        'notifications': Notification,
    }

    table_names = list(MODEL_MAP.keys())

    # Count rows for sidebar summary
    table_counts = {}
    for key, model in MODEL_MAP.items():
        try:
            table_counts[key] = db.session.query(db.func.count(model.id)).scalar() or 0
        except Exception:
            table_counts[key] = 0
    table_counts_list = list(table_counts.items())

    # Determine which table is selected
    current_table = request.args.get('table', table_names[0])
    if current_table not in MODEL_MAP:
        current_table = table_names[0]

    model = MODEL_MAP[current_table]
    page  = request.args.get('page', 1, type=int)

    # ── Schema: read directly from model.__table__.columns (always correct) ────
    table_schema = []
    col_names    = []
    try:
        sa_table = model.__table__
        pk_names = {c.name for c in sa_table.primary_key}
        fk_names = {list(c.foreign_keys)[0].parent.name
                    for c in sa_table.columns if c.foreign_keys}
        for col in sa_table.columns:
            table_schema.append({
                'name':        col.name,
                'type':        str(col.type),
                'nullable':    col.nullable,
                'primary_key': col.name in pk_names,
                'foreign_key': col.name in fk_names,
            })
        col_names = [c['name'] for c in table_schema]
    except Exception as exc:
        current_app.logger.error(f'database_viewer schema error: {exc}')

    # ── Data: paginate ORM rows and serialise each to a plain dict ────────────
    try:
        pagination = model.query.order_by(model.id.desc()).paginate(
            page=page, per_page=PER_PAGE, error_out=False
        )
        items = []
        for row in pagination.items:
            row_dict = {}
            for col_name in col_names:
                val = getattr(row, col_name, None)
                if val is None:
                    row_dict[col_name] = 'NULL'
                elif isinstance(val, (list, dict)):
                    row_dict[col_name] = json.dumps(val, ensure_ascii=False)
                elif hasattr(val, 'isoformat'):      # datetime / date / time
                    row_dict[col_name] = val.isoformat()
                else:
                    row_dict[col_name] = val
            items.append(row_dict)

        table_data = {
            'items':        items,
            'total':        pagination.total,
            'pages':        pagination.pages,
            'current_page': page,
            'has_prev':     pagination.has_prev,
            'has_next':     pagination.has_next,
        }
    except Exception as exc:
        table_data = {
            'items':        [],
            'total':        0,
            'pages':        1,
            'current_page': 1,
            'has_prev':     False,
            'has_next':     False,
            'error':        str(exc),
        }

    return render_template(
        'database_viewer.html',
        current_table=current_table,
        table_names=table_names,
        table_counts=table_counts,
        table_counts_list=table_counts_list,
        table_schema=table_schema,
        table_data=table_data,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESTAURANT MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/restaurants')
@login_required
@admin_required
def restaurants():
    rests = Restaurant.query.order_by(Restaurant.created_at.desc()).all()
    return render_template('admin/restaurants.html', restaurants=rests)


@admin.route('/restaurants/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_restaurant():
    if request.method == 'POST':
        try:
            image_filename = 'restaurant_default.jpg'
            if 'image' in request.files:
                saved, err = save_image(request.files['image'])
                if saved:
                    image_filename = saved

            restaurant = Restaurant(
                name=request.form.get('name'),
                location=request.form.get('location'),
                cuisine_type=request.form.get('cuisine_type'),
                description=request.form.get('description'),
                delivery_time=request.form.get('delivery_time', 30, type=int),
                min_order=request.form.get('min_order', 0.0, type=float),
                delivery_fee=request.form.get('delivery_fee', 40.0, type=float),
                phone=request.form.get('phone'),
                opening_time=request.form.get('opening_time', '09:00'),
                closing_time=request.form.get('closing_time', '22:00'),
                is_active=request.form.get('is_active') == 'on',
                image=image_filename,
            )
            db.session.add(restaurant)
            db.session.commit()

            log_admin_activity('Added Restaurant', 'restaurant', restaurant.id,
                               f'Added: {restaurant.name}')
            broadcast_update('restaurant_added', {'id': restaurant.id, 'name': restaurant.name})

            flash('Restaurant added successfully!', 'success')
            return redirect(url_for('admin.restaurants'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding restaurant: {str(e)}', 'error')

    return render_template('admin/add_restaurant.html')


@admin.route('/restaurants/edit/<int:restaurant_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)

    if request.method == 'POST':
        try:
            if 'image' in request.files and request.files['image'].filename:
                saved, err = save_image(request.files['image'], restaurant.image)
                if saved:
                    restaurant.image = saved

            restaurant.name          = request.form.get('name', restaurant.name)
            restaurant.location      = request.form.get('location', restaurant.location)
            restaurant.cuisine_type  = request.form.get('cuisine_type', restaurant.cuisine_type)
            restaurant.description   = request.form.get('description', restaurant.description)
            restaurant.delivery_time = request.form.get('delivery_time', restaurant.delivery_time, type=int)
            restaurant.min_order     = request.form.get('min_order', restaurant.min_order, type=float)
            restaurant.delivery_fee  = request.form.get('delivery_fee', restaurant.delivery_fee, type=float)
            restaurant.phone         = request.form.get('phone', restaurant.phone)
            restaurant.opening_time  = request.form.get('opening_time', restaurant.opening_time)
            restaurant.closing_time  = request.form.get('closing_time', restaurant.closing_time)
            restaurant.is_active     = request.form.get('is_active') == 'on'

            db.session.commit()
            log_admin_activity('Updated Restaurant', 'restaurant', restaurant.id,
                               f'Updated: {restaurant.name}')
            broadcast_update('restaurant_updated', {'id': restaurant.id})
            flash('Restaurant updated successfully!', 'success')
            return redirect(url_for('admin.restaurants'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating restaurant: {str(e)}', 'error')

    return render_template('admin/edit_restaurant.html', restaurant=restaurant)


@admin.route('/api/restaurant/<int:restaurant_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_restaurant(restaurant_id):
    if request.method == 'GET':
        r = Restaurant.query.get_or_404(restaurant_id)
        return jsonify({'success': True, 'data': {
            'id': r.id, 'name': r.name, 'location': r.location,
            'cuisine_type': r.cuisine_type, 'description': r.description,
            'image': r.image, 'delivery_time': r.delivery_time,
            'min_order': r.min_order, 'delivery_fee': r.delivery_fee,
            'is_active': r.is_active,
        }})

    elif request.method == 'PUT':
        try:
            r    = Restaurant.query.get_or_404(restaurant_id)
            data = request.get_json() or {}
            for field in ('name', 'location', 'cuisine_type', 'description', 'is_active'):
                if field in data:
                    setattr(r, field, data[field])
            if 'delivery_time' in data:
                r.delivery_time = int(data['delivery_time'])
            if 'min_order' in data:
                r.min_order = float(data['min_order'])
            if 'delivery_fee' in data:
                r.delivery_fee = float(data['delivery_fee'])
            db.session.commit()
            log_admin_activity('Updated Restaurant', 'restaurant', restaurant_id)
            return jsonify({'success': True, 'message': 'Updated'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            r = Restaurant.query.get(restaurant_id)
            if not r:
                return jsonify({'success': False, 'message': 'Not found'}), 404
            name = r.name
            # Cascades handle food_items deletion (defined in model)
            db.session.delete(r)
            db.session.commit()
            log_admin_activity('Deleted Restaurant', 'restaurant', restaurant_id,
                               f'Deleted: {name}')
            broadcast_update('restaurant_deleted', {'id': restaurant_id})
            return jsonify({'success': True, 'message': f'Restaurant "{name}" deleted'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/restaurant', methods=['POST'])
@login_required
@admin_required
def api_add_restaurant():
    try:
        image_filename = 'restaurant_default.jpg'
        if 'image' in request.files:
            saved, err = save_image(request.files['image'])
            if saved:
                image_filename = saved

        r = Restaurant(
            name=request.form.get('name'),
            location=request.form.get('location', ''),
            cuisine_type=request.form.get('cuisine_type', ''),
            description=request.form.get('description', ''),
            delivery_time=int(request.form.get('delivery_time', 30)),
            min_order=float(request.form.get('min_order', 0)),
            delivery_fee=float(request.form.get('delivery_fee', 40)),
            image=image_filename,
        )
        db.session.add(r)
        db.session.commit()
        log_admin_activity('Added Restaurant', 'restaurant', r.id)
        return jsonify({'success': True, 'message': 'Restaurant added', 'id': r.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# DISH MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/dishes')
@login_required
@admin_required
def dishes():
    dish_list   = FoodItem.query.order_by(FoodItem.created_at.desc()).all()
    rest_list   = Restaurant.query.all()
    return render_template('admin/dishes.html', dishes=dish_list, restaurants=rest_list)


@admin.route('/dishes/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_dish():
    if request.method == 'POST':
        try:
            image_filename = 'food_default.jpg'
            if 'image' in request.files:
                saved, _ = save_image(request.files['image'])
                if saved:
                    image_filename = saved

            dish = FoodItem(
                name=request.form.get('name'),
                description=request.form.get('description'),
                price=float(request.form.get('price', 0)),
                restaurant_id=int(request.form.get('restaurant_id')),
                category=request.form.get('category', 'Main Course'),
                is_vegetarian='is_vegetarian' in request.form,
                is_vegan='is_vegan' in request.form,
                is_gluten_free='is_gluten_free' in request.form,
                is_available=request.form.get('is_available') == 'on',
                image=image_filename,
            )
            db.session.add(dish)
            db.session.commit()
            log_admin_activity('Added Dish', 'dish', dish.id, f'Added: {dish.name}')
            broadcast_update('dish_added', {'id': dish.id, 'name': dish.name})
            flash('Dish added successfully!', 'success')
            return redirect(url_for('admin.dishes'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding dish: {str(e)}', 'error')

    rest_list = Restaurant.query.all()
    return render_template('admin/add_dish.html', restaurants=rest_list)


@admin.route('/dishes/edit/<int:dish_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_dish(dish_id):
    dish = FoodItem.query.get_or_404(dish_id)

    if request.method == 'POST':
        try:
            if 'image' in request.files and request.files['image'].filename:
                saved, _ = save_image(request.files['image'], dish.image)
                if saved:
                    dish.image = saved

            dish.name           = request.form.get('name', dish.name)
            dish.description    = request.form.get('description', dish.description)
            dish.price          = float(request.form.get('price', dish.price))
            dish.category       = request.form.get('category', dish.category)
            dish.restaurant_id  = int(request.form.get('restaurant_id', dish.restaurant_id))
            dish.is_vegetarian  = 'is_vegetarian' in request.form
            dish.is_vegan       = 'is_vegan' in request.form
            dish.is_gluten_free = 'is_gluten_free' in request.form
            dish.is_available   = request.form.get('is_available') == 'on'

            db.session.commit()
            log_admin_activity('Updated Dish', 'dish', dish.id)
            flash('Dish updated successfully!', 'success')
            return redirect(url_for('admin.dishes'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating dish: {str(e)}', 'error')

    rest_list = Restaurant.query.all()
    return render_template('admin/edit_dish.html', dish=dish, restaurants=rest_list)


@admin.route('/dishes/delete/<int:dish_id>', methods=['POST'])
@login_required
@admin_required
def delete_dish(dish_id):
    try:
        dish = FoodItem.query.get_or_404(dish_id)
        name = dish.name
        db.session.delete(dish)
        db.session.commit()
        log_admin_activity('Deleted Dish', 'dish', dish_id, f'Deleted: {name}')
        flash('Dish deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting dish: {str(e)}', 'error')
    return redirect(url_for('admin.dishes'))


@admin.route('/api/dish', methods=['POST'])
@login_required
@admin_required
def api_add_dish():
    try:
        image_filename = 'food_default.jpg'
        if 'image' in request.files and request.files['image'].filename:
            saved, _ = save_image(request.files['image'])
            if saved:
                image_filename = saved

        dish = FoodItem(
            name=request.form.get('name'),
            description=request.form.get('description', ''),
            price=float(request.form.get('price', 0)),
            restaurant_id=int(request.form.get('restaurant_id')),
            category=request.form.get('category', 'Main Course'),
            is_vegetarian='is_vegetarian' in request.form,
            is_vegan='is_vegan' in request.form,
            is_gluten_free='is_gluten_free' in request.form,
            is_available=True,
            image=image_filename,
        )
        db.session.add(dish)
        db.session.commit()
        log_admin_activity('Added Dish', 'dish', dish.id)
        return jsonify({'success': True, 'message': 'Dish added', 'id': dish.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/dish/<int:dish_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_dish(dish_id):
    """Get, update, or delete a single dish (used by admin dishes page JS)."""
    dish = FoodItem.query.get_or_404(dish_id)

    if request.method == 'GET':
        return jsonify({
            'success':       True,
            'id':            dish.id,
            'name':          dish.name,
            'description':   dish.description,
            'price':         float(dish.price),
            'category':      dish.category,
            'restaurant_id': dish.restaurant_id,
            'restaurant':    dish.restaurant.name if dish.restaurant else '',
            'is_available':  dish.is_available,
            'is_vegetarian': dish.is_vegetarian,
            'is_vegan':      dish.is_vegan,
            'is_gluten_free':dish.is_gluten_free,
            'is_bestseller': dish.is_bestseller,
            'image':         dish.image,
            'calories':      dish.calories,
        })

    if request.method == 'PUT':
        try:
            # Support both JSON and form-data
            if request.content_type and 'application/json' in request.content_type:
                data = request.get_json() or {}
                def get(k, default=None): return data.get(k, default)
            else:
                def get(k, default=None): return request.form.get(k, default)

            dish.name        = get('name', dish.name)
            dish.description = get('description', dish.description)
            dish.category    = get('category', dish.category)
            dish.is_available   = bool(get('is_available', dish.is_available))
            dish.is_vegetarian  = bool(get('is_vegetarian', dish.is_vegetarian))
            dish.is_vegan       = bool(get('is_vegan', dish.is_vegan))
            dish.is_gluten_free = bool(get('is_gluten_free', dish.is_gluten_free))
            dish.is_bestseller  = bool(get('is_bestseller', dish.is_bestseller))

            price_val = get('price')
            if price_val is not None:
                dish.price = float(price_val)

            cal = get('calories')
            if cal is not None:
                dish.calories = int(cal) if cal else None

            if 'image' in request.files and request.files['image'].filename:
                saved, _ = save_image(request.files['image'])
                if saved:
                    dish.image = saved

            db.session.commit()
            log_admin_activity('Updated Dish', 'dish', dish.id)
            return jsonify({'success': True, 'message': f'Dish "{dish.name}" updated'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    if request.method == 'DELETE':
        try:
            name = dish.name
            db.session.delete(dish)
            db.session.commit()
            log_admin_activity('Deleted Dish', 'dish', dish_id)
            return jsonify({'success': True, 'message': f'Dish "{name}" deleted'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500



# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/users')
@login_required
@admin_required
def users():
    page     = request.args.get('page', 1, type=int)
    q        = request.args.get('q', '')
    role_f   = request.args.get('role', '')

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
        u         = User.query.get_or_404(user_id)
        orders    = Order.query.filter_by(user_id=user_id).all()
        total_spent = sum(o.total_amount for o in orders if o.total_amount)
        reviews   = Review.query.filter_by(user_id=user_id).all()
        avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0

        return jsonify({
            'success': True,
            'user': {
                'id':              u.id,
                'name':            u.name,
                'email':           u.email,
                'contact':         u.contact,
                'address':         u.address,
                'profile_photo':   u.profile_photo,   # fixed: was profile_picture
                'is_active':       u.is_active,
                'role':            u.role,
                'created_at':      u.created_at.isoformat() if u.created_at else None,
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


# ─────────────────────────────────────────────────────────────────────────────
# ORDER MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/orders')
@login_required
@admin_required
def orders():
    page       = request.args.get('page', 1, type=int)
    status_f   = request.args.get('status', '')
    query      = Order.query
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
        order        = Order.query.get_or_404(order_id)
        order.status = new_status
        order.updated_at = datetime.now(timezone.utc)
        # H8 fix: stamp delivery timestamp on delivered status (admin path)
        if new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = datetime.now(timezone.utc)

        # Append to status history
        history = OrderStatusHistory(
            order_id=order_id, status=new_status,
            note=f'Status changed by admin {current_user.name}',
        )
        db.session.add(history)

        # Notify customer
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


# ─────────────────────────────────────────────────────────────────────────────
# BLOG MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/blogs')
@login_required
@admin_required
def admin_blogs():
    blog_list = Blog.query.order_by(Blog.created_at.desc()).all()
    return render_template('admin/blogs.html', blogs=blog_list)


# Alias expected by some broadcast redirects
admin_blogs_list = admin_blogs


@admin.route('/blogs/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_blog():
    if request.method == 'POST':
        try:
            image_filename = 'blog_default.jpg'
            if 'image' in request.files:
                saved, _ = save_image(request.files['image'])
                if saved:
                    image_filename = saved

            blog = Blog(
                title=request.form.get('title'),
                content=request.form.get('content'),
                excerpt=request.form.get('excerpt', ''),
                author=current_user.name,    # fixed: was current_user.username
                category=request.form.get('category', 'Food'),
                status=request.form.get('status', 'published'),
                featured=request.form.get('featured') == 'on',
                image=image_filename,
            )
            blog.generate_slug()
            db.session.add(blog)
            db.session.commit()
            log_admin_activity('Added Blog', 'blog', blog.id, f'Added: {blog.title}')
            flash('Blog post added successfully!', 'success')
            return redirect(url_for('admin.admin_blogs'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding blog: {str(e)}', 'error')

    return render_template('admin/add_blog.html')


@admin.route('/blogs/edit/<int:blog_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_blog(blog_id):
    blog = Blog.query.get_or_404(blog_id)

    if request.method == 'POST':
        try:
            if 'image' in request.files and request.files['image'].filename:
                saved, _ = save_image(request.files['image'], blog.image)
                if saved:
                    blog.image = saved

            blog.title    = request.form.get('title', blog.title)
            blog.content  = request.form.get('content', blog.content)
            blog.excerpt  = request.form.get('excerpt', blog.excerpt)
            blog.category = request.form.get('category', blog.category)
            blog.status   = request.form.get('status', blog.status)
            blog.featured = request.form.get('featured') == 'on'

            db.session.commit()
            log_admin_activity('Updated Blog', 'blog', blog.id)
            flash('Blog updated successfully!', 'success')
            return redirect(url_for('admin.admin_blogs'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating blog: {str(e)}', 'error')

    return render_template('admin/edit_blog.html', blog=blog)


@admin.route('/blogs/delete/<int:blog_id>', methods=['POST'])
@login_required
@admin_required
def delete_blog(blog_id):
    try:
        blog = Blog.query.get_or_404(blog_id)
        title = blog.title
        db.session.delete(blog)
        db.session.commit()
        log_admin_activity('Deleted Blog', 'blog', blog_id, f'Deleted: {title}')
        flash('Blog deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting blog: {str(e)}', 'error')
    return redirect(url_for('admin.admin_blogs'))


# ─────────────────────────────────────────────────────────────────────────────
# OFFERS MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/offers')
@login_required
@admin_required
def offers():
    offer_list = Offer.query.order_by(Offer.created_at.desc()).all()
    return render_template('admin/offers.html', offers=offer_list)


@admin.route('/offers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_offer():
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%dT%H:%M')
            end_date   = datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%dT%H:%M')

            offer = Offer(
                title=request.form.get('title'),
                description=request.form.get('description'),
                discount_type=request.form.get('discount_type'),
                discount_value=float(request.form.get('discount_value', 0)),
                min_order_amount=float(request.form.get('min_order_amount', 0)),
                max_discount=request.form.get('max_discount', None, type=float),
                code=request.form.get('code', '').upper() or None,
                start_date=start_date,
                end_date=end_date,
                usage_limit=request.form.get('usage_limit', None, type=int),
                is_active=request.form.get('is_active') == 'on',
            )
            db.session.add(offer)
            db.session.commit()
            log_admin_activity('Added Offer', 'offer', offer.id)
            flash('Offer added successfully!', 'success')
            return redirect(url_for('admin.offers'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding offer: {str(e)}', 'error')

    return render_template('admin/offers.html', offers=Offer.query.all(), show_add_form=True)


@admin.route('/offers/toggle/<int:offer_id>', methods=['POST'])
@login_required
@admin_required
def toggle_offer(offer_id):
    try:
        offer = Offer.query.get_or_404(offer_id)
        offer.is_active = not offer.is_active
        db.session.commit()
        status = 'activated' if offer.is_active else 'deactivated'
        flash(f'Offer {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('admin.offers'))


# ─────────────────────────────────────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/reviews')
@login_required
@admin_required
def reviews():
    review_list = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=review_list)


@admin.route('/api/review/<int:review_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_review(review_id):
    try:
        review = Review.query.get_or_404(review_id)
        review.is_approved = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/review/<int:review_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_review(review_id):
    try:
        review = Review.query.get_or_404(review_id)
        db.session.delete(review)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENTS
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/payments')
@login_required
@admin_required
def payments():
    payment_list = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payments.html', payments=payment_list)


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────
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

        # Target user selection
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


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/support')
@login_required
@admin_required
def support():
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return render_template('admin/support.html', tickets=tickets)


# ─────────────────────────────────────────────────────────────────────────────
# MENU MANAGEMENT APIs (used by JavaScript managers)
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/api/restaurant/<int:restaurant_id>/menu', methods=['GET'])
@login_required
@admin_required
def get_menu(restaurant_id):
    items = FoodItem.query.filter_by(restaurant_id=restaurant_id).all()
    return jsonify({'items': [{
        'id':           i.id,
        'name':         i.name,
        'price':        float(i.price),
        'description':  i.description,
        'category':     i.category,
        'image':        i.image,
        'is_available': i.is_available,
    } for i in items]})


@admin.route('/api/menu-item', methods=['POST'])
@login_required
@admin_required
def add_menu_item():
    try:
        filename = 'food_default.jpg'
        if 'image' in request.files:
            saved, _ = save_image(request.files['image'])
            if saved:
                filename = saved

        item = FoodItem(
            restaurant_id=int(request.form['restaurant_id']),
            name=request.form['name'],
            price=float(request.form['price']),
            description=request.form.get('description', ''),
            category=request.form.get('category', 'Main Course'),
            image=filename,
            is_available=True,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Menu item added', 'id': item.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/menu-item/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_menu_item(item_id):
    if request.method == 'GET':
        i = FoodItem.query.get_or_404(item_id)
        return jsonify({
            'id': i.id, 'name': i.name, 'price': float(i.price),
            'description': i.description, 'category': i.category,
            'image': i.image, 'is_available': i.is_available,
        })

    elif request.method == 'PUT':
        try:
            i = FoodItem.query.get_or_404(item_id)
            if 'image' in request.files and request.files['image'].filename:
                saved, _ = save_image(request.files['image'], i.image)
                if saved:
                    i.image = saved
            i.name         = request.form.get('name', i.name)
            i.price        = float(request.form.get('price', i.price))
            i.description  = request.form.get('description', i.description)
            i.category     = request.form.get('category', i.category)
            i.is_available = request.form.get('is_available', 'true').lower() == 'true'
            db.session.commit()
            return jsonify({'success': True, 'message': 'Updated'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            i = FoodItem.query.get_or_404(item_id)
            db.session.delete(i)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Deleted'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# BLOG APIs
# ─────────────────────────────────────────────────────────────────────────────
@admin.route('/api/blog', methods=['POST'])
@login_required
@admin_required
def api_add_blog():
    try:
        filename = 'blog_default.jpg'
        if 'image' in request.files:
            saved, _ = save_image(request.files['image'])
            if saved:
                filename = saved

        blog = Blog(
            title=request.form.get('title'),
            content=request.form.get('content'),
            author=current_user.name,   # fixed: was current_user.username
            excerpt=request.form.get('excerpt', ''),
            category=request.form.get('category', 'Food'),
            status='published',
            image=filename,
        )
        blog.generate_slug()
        db.session.add(blog)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Blog added', 'id': blog.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/blog/<int:blog_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_blog(blog_id):
    if request.method == 'GET':
        b = Blog.query.get_or_404(blog_id)
        return jsonify({'id': b.id, 'title': b.title, 'content': b.content,
                        'author': b.author, 'excerpt': b.excerpt,
                        'category': b.category, 'image': b.image, 'status': b.status})

    elif request.method == 'PUT':
        try:
            b = Blog.query.get_or_404(blog_id)
            if 'image' in request.files and request.files['image'].filename:
                saved, _ = save_image(request.files['image'], b.image)
                if saved:
                    b.image = saved
            b.title    = request.form.get('title', b.title)
            b.content  = request.form.get('content', b.content)
            b.excerpt  = request.form.get('excerpt', b.excerpt)
            b.category = request.form.get('category', b.category)
            b.status   = request.form.get('status', b.status)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500

    elif request.method == 'DELETE':
        try:
            b = Blog.query.get_or_404(blog_id)
            db.session.delete(b)
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# ROLE MANAGEMENT — promote/demote users, assign restaurant owners
# ─────────────────────────────────────────────────────────────────────────────

@admin.route('/api/user/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    """Change a user's role. Prevents self-demotion."""
    data = request.get_json() or {}
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
    log_admin_activity('Changed User Role', 'user', user_id, f'{old_role} → {new_role}')
    return jsonify({'success': True, 'message': f'Role updated to {new_role}'})


@admin.route('/api/user/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Hard-delete a user. Prevents self-deletion and last-admin deletion."""
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete your own account.'}), 403
    u = User.query.get_or_404(user_id)
    # H7 fix: never delete the last admin — that would lock everyone out.
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


@admin.route('/api/restaurant/<int:restaurant_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_restaurant(restaurant_id):
    """Approve a pending restaurant so it appears on the platform."""
    r = Restaurant.query.get_or_404(restaurant_id)
    r.is_approved = True
    r.is_active   = True
    db.session.commit()
    # Notify owner
    if r.owner_id:
        db.session.add(Notification(
            user_id=r.owner_id,
            title='🎉 Your restaurant is approved!',
            message=f'"{r.name}" is now live on GrabBite. Start adding your menu!',
            type='general',
            link='/owner/dishes',
        ))
        db.session.commit()
    log_admin_activity('Approved Restaurant', 'restaurant', restaurant_id, f'Approved: {r.name}')
    return jsonify({'success': True, 'message': f'"{r.name}" approved and live.'})


@admin.route('/api/restaurant/<int:restaurant_id>/assign-owner', methods=['POST'])
@login_required
@admin_required
def assign_restaurant_owner(restaurant_id):
    """Assign a user as the owner of a restaurant."""
    data    = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'user_id required'}), 400
    u = User.query.get_or_404(user_id)
    r = Restaurant.query.get_or_404(restaurant_id)
    r.owner_id = u.id
    u.role = 'restaurant_owner'
    db.session.commit()
    log_admin_activity('Assigned Owner', 'restaurant', restaurant_id,
                       f'User {u.name} → {r.name}')
    return jsonify({'success': True, 'message': f'{u.name} is now owner of {r.name}'})


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT — CSV download for orders, users, payments
# ─────────────────────────────────────────────────────────────────────────────

# M18 fix: prevent CSV formula injection (CWE-1236). Cells whose first
# character is one of = + - @ (tab) (CR) get prefixed with a single quote so
# Excel / LibreOffice don't interpret them as formulas.
CSV_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def csv_safe(value) -> str:
    s = '' if value is None else str(value)
    if s and s[0] in CSV_FORMULA_PREFIXES:
        s = "'" + s
    return s


@admin.route('/export/orders')
@login_required
@admin_required
def export_orders():
    """Download all orders as CSV."""
    import csv
    import io
    from flask import Response

    orders = Order.query.order_by(Order.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User', 'Restaurant', 'Amount', 'Status',
                     'Payment Method', 'Payment Status', 'Date'])
    for o in orders:
        writer.writerow([
            o.id,
            csv_safe(o.user.name if o.user else ''),
            csv_safe(o.restaurant.name if o.restaurant else ''),
            o.total_amount,
            csv_safe(o.status),
            csv_safe(o.payment_method),
            csv_safe(o.payment_status),
            csv_safe(o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else ''),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=orders.csv'},
    )


@admin.route('/export/users')
@login_required
@admin_required
def export_users():
    """Download all users as CSV."""
    import csv
    import io
    from flask import Response

    users = User.query.order_by(User.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Role',
                     'Active', 'Joined', 'Last Login'])
    for u in users:
        writer.writerow([
            u.id, csv_safe(u.name), csv_safe(u.email), csv_safe(u.phone or u.contact),
            csv_safe(u.role), u.is_active,
            csv_safe(u.created_at.strftime('%Y-%m-%d') if u.created_at else ''),
            csv_safe(u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else ''),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=users.csv'},
    )


@admin.route('/export/payments')
@login_required
@admin_required
def export_payments():
    """Download all payments as CSV."""
    import csv
    import io
    from flask import Response

    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Order ID', 'Amount', 'Method', 'Status',
                     'Gateway', 'Gateway Payment ID', 'Date'])
    for p in payments:
        writer.writerow([
            p.id, p.order_id, p.amount, csv_safe(p.payment_method),
            csv_safe(p.status), csv_safe(p.gateway),
            csv_safe(p.gateway_payment_id or ''),
            csv_safe(p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ''),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=payments.csv'},
    )
