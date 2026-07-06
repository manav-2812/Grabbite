"""
Grabbite — API: Cart
/api/cart/count, /api/cart (GET), /api/cart/add, /api/cart/update,
/api/cart/remove, /api/cart/clear
"""
from flask import request, jsonify, url_for, current_app
from flask_login import current_user, login_required

from db import db
from models import Cart, FoodItem, Restaurant
from blueprints.api import api_bp


@api_bp.route('/api/cart/count')
def api_cart_count():
    if not current_user.is_authenticated:
        return jsonify({'count': 0})
    count = Cart.query.filter_by(user_id=current_user.id).count()
    return jsonify({'count': count})


@api_bp.route('/api/cart', methods=['GET'])
@login_required
def api_cart_get():
    """Return full cart as JSON for frontend sync."""
    cart_rows = db.session.query(Cart, FoodItem, Restaurant)\
        .join(FoodItem, Cart.food_item_id == FoodItem.id)\
        .join(Restaurant, FoodItem.restaurant_id == Restaurant.id)\
        .filter(Cart.user_id == current_user.id).all()

    items = [{
        'cart_id':         c.id,
        'food_id':         f.id,
        'food_name':       f.name,
        'restaurant_id':   r.id,
        'restaurant_name': r.name,
        'price':           float(f.price),
        'quantity':        c.quantity,
        'notes':           c.notes or '',
        'image':           f.image,
        'item_total':      float(c.quantity * f.price),
    } for c, f, r in cart_rows]

    subtotal     = sum(i['item_total'] for i in items)
    tax          = round(subtotal * 0.18, 2)
    delivery_fee = 0.0 if subtotal > 500 else 40.0
    total        = round(subtotal + tax + delivery_fee, 2)

    return jsonify({
        'success': True,
        'items':   items,
        'summary': {
            'subtotal':     subtotal,
            'tax':          tax,
            'delivery_fee': delivery_fee,
            'total':        total,
            'count':        len(items),
        }
    })


@api_bp.route('/api/cart/add', methods=['POST'])
def api_cart_add():
    """Add item to cart — works from ANY page (restaurant, search, home, etc.)."""
    if not current_user.is_authenticated:
        return jsonify({
            'success': False,
            'message': 'Please login to add items to cart',
            'redirect': url_for('account.login'),
        }), 401

    try:
        data         = request.get_json() or {}
        food_item_id = data.get('food_item_id')
        quantity     = max(1, int(data.get('quantity', 1)))
        notes        = data.get('notes', '')

        if not food_item_id:
            return jsonify({'success': False, 'message': 'food_item_id is required'}), 400

        food_item = FoodItem.query.get(food_item_id)
        if not food_item:
            return jsonify({'success': False, 'message': 'Food item not found'}), 404
        if not food_item.is_available:
            return jsonify({'success': False, 'message': 'This item is currently unavailable'}), 400

        existing = Cart.query.filter_by(
            user_id=current_user.id, food_item_id=food_item_id
        ).first()

        if existing:
            existing.quantity += quantity
            existing.price = food_item.price
            if notes:
                existing.notes = notes
        else:
            cart_item = Cart(
                user_id=current_user.id,
                food_item_id=food_item_id,
                quantity=quantity,
                price=food_item.price,
                notes=notes or None,
            )
            db.session.add(cart_item)

        db.session.commit()
        cart_count = Cart.query.filter_by(user_id=current_user.id).count()

        return jsonify({
            'success':    True,
            'message':    f'{food_item.name} added to cart!',
            'cart_count': cart_count,
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'api_cart_add error: {e}')
        return jsonify({'success': False, 'message': 'Error adding to cart'}), 500


@api_bp.route('/api/cart/update', methods=['POST'])
@login_required
def api_cart_update():
    data     = request.get_json() or {}
    cart_id  = data.get('cart_id')
    quantity = data.get('quantity', 1)

    cart_item = Cart.query.filter_by(id=cart_id, user_id=current_user.id).first()
    if not cart_item:
        return jsonify({'success': False, 'message': 'Cart item not found'}), 404

    try:
        food_item = FoodItem.query.get(cart_item.food_item_id)
        if not food_item:
            return jsonify({'success': False, 'message': 'Food item not found'}), 404

        cart_item.quantity = int(quantity)
        cart_item.price    = food_item.price
        db.session.commit()

        all_items    = db.session.query(Cart, FoodItem)\
            .join(FoodItem, Cart.food_item_id == FoodItem.id)\
            .filter(Cart.user_id == current_user.id).all()
        subtotal     = sum(c.quantity * f.price for c, f in all_items)
        tax          = round(subtotal * 0.18, 2)
        delivery_fee = 0.0 if subtotal > 500 else 40.0
        item_total   = cart_item.quantity * food_item.price

        return jsonify({
            'success':     True,
            'message':     'Cart updated',
            'item_total':  float(item_total),
            'summary':     {
                'subtotal':     subtotal,
                'tax':          tax,
                'delivery_fee': delivery_fee,
                'total':        round(subtotal + tax + delivery_fee, 2),
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error updating cart'}), 500


@api_bp.route('/api/cart/remove', methods=['POST'])
@login_required
def api_cart_remove():
    data    = request.get_json() or {}
    cart_id = data.get('cart_id')

    cart_item = Cart.query.filter_by(id=cart_id, user_id=current_user.id).first()
    if not cart_item:
        return jsonify({'success': False, 'message': 'Cart item not found'}), 404

    try:
        db.session.delete(cart_item)
        db.session.commit()
        cart_count = Cart.query.filter_by(user_id=current_user.id).count()
        return jsonify({'success': True, 'message': 'Item removed', 'cart_count': cart_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error removing item'}), 500


@api_bp.route('/api/cart/clear', methods=['POST'])
@login_required
def api_cart_clear():
    try:
        Cart.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cart cleared'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error clearing cart'}), 500
