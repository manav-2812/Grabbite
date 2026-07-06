"""
Grabbite — Admin: Restaurant Management
/admin/restaurants/*, /admin/api/restaurant/*,
/admin/api/restaurant/<id>/menu, /admin/api/menu-item/*,
/admin/api/restaurant/<id>/approve, /admin/api/restaurant/<id>/assign-owner
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from db import db
from models import Restaurant, FoodItem, User, Notification
from blueprints.admin import admin, save_image, log_admin_activity, broadcast_update
from utils.decorators import admin_required


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


# ── Menu management (belongs with restaurants) ────────────────────────────────

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


@admin.route('/api/restaurant/<int:restaurant_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_restaurant(restaurant_id):
    """Approve a pending restaurant so it appears on the platform."""
    r = Restaurant.query.get_or_404(restaurant_id)
    r.is_approved = True
    r.is_active   = True
    db.session.commit()
    if r.owner_id:
        db.session.add(Notification(
            user_id=r.owner_id,
            title='Your restaurant is approved!',
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
                       f'User {u.name} -> {r.name}')
    return jsonify({'success': True, 'message': f'{u.name} is now owner of {r.name}'})
