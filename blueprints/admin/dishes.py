"""
Grabbite — Admin: Dish Management
/admin/dishes/*, /admin/api/dish/*
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required

from db import db
from models import FoodItem, Restaurant
from blueprints.admin import admin, save_image, log_admin_activity, broadcast_update
from utils.decorators import admin_required


@admin.route('/dishes')
@login_required
@admin_required
def dishes():
    dish_list = FoodItem.query.order_by(FoodItem.created_at.desc()).all()
    rest_list = Restaurant.query.all()
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
            'success':        True,
            'id':             dish.id,
            'name':           dish.name,
            'description':    dish.description,
            'price':          float(dish.price),
            'category':       dish.category,
            'restaurant_id':  dish.restaurant_id,
            'restaurant':     dish.restaurant.name if dish.restaurant else '',
            'is_available':   dish.is_available,
            'is_vegetarian':  dish.is_vegetarian,
            'is_vegan':       dish.is_vegan,
            'is_gluten_free': dish.is_gluten_free,
            'is_bestseller':  dish.is_bestseller,
            'image':          dish.image,
            'calories':       dish.calories,
        })

    if request.method == 'PUT':
        try:
            if request.content_type and 'application/json' in request.content_type:
                data = request.get_json() or {}
                def get(k, default=None): return data.get(k, default)
            else:
                def get(k, default=None): return request.form.get(k, default)

            dish.name           = get('name', dish.name)
            dish.description    = get('description', dish.description)
            dish.category       = get('category', dish.category)
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
