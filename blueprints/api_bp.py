"""
Grabbite — API Blueprint
HIGH-4: Extracted from app.py as part of the blueprint refactor.
All /api/* endpoints except /api/payment/* (which live in blueprints/payment.py).
"""
import os as _os
import json as _json
from datetime import datetime, timezone
from typing import cast

from flask import Blueprint, request, jsonify, url_for, current_app
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from db import db
from models import (Cart, FoodItem, Restaurant, Wishlist, Review, User,
                    Offer, CouponUsage, Address, Notification, Blog)

api_bp = Blueprint('api', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# CART APIs
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# WISHLIST API
# ─────────────────────────────────────────────────────────────────────────────
@api_bp.route('/api/wishlist/toggle', methods=['POST'])
@login_required
def api_wishlist_toggle():
    data          = request.get_json() or {}
    restaurant_id = data.get('restaurant_id')

    if not restaurant_id:
        return jsonify({'success': False, 'message': 'restaurant_id required'}), 400

    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant not found'}), 404

    try:
        existing = Wishlist.query.filter_by(
            user_id=current_user.id, restaurant_id=restaurant_id
        ).with_for_update(read=False).first()

        if existing:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'success': True, 'wishlisted': False, 'message': 'Removed from wishlist'})

        item = Wishlist(user_id=current_user.id, restaurant_id=restaurant_id)
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'wishlisted': True, 'message': 'Added to wishlist'})
    except IntegrityError:
        db.session.rollback()
        exists = Wishlist.query.filter_by(
            user_id=current_user.id, restaurant_id=restaurant_id
        ).first() is not None
        return jsonify({
            'success': True,
            'wishlisted': exists,
            'message': 'Already in wishlist' if exists else 'Removed from wishlist'
        })


# ─────────────────────────────────────────────────────────────────────────────
# COUPON API
# ─────────────────────────────────────────────────────────────────────────────
@api_bp.route('/api/coupon/apply', methods=['POST'])
@login_required
def api_coupon_apply():
    data       = request.get_json() or {}
    code       = (data.get('code') or '').strip().upper()
    cart_total = float(data.get('cart_total', 0))

    if not code:
        return jsonify({'success': False, 'message': 'Coupon code required'}), 400

    offer = Offer.query.filter_by(code=code).first()
    if not offer:
        return jsonify({'success': False, 'message': 'Invalid coupon code'}), 404

    valid, msg = offer.is_valid()
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400

    if cart_total < offer.min_order_amount:
        return jsonify({
            'success': False,
            'message': f'Min order ₹{offer.min_order_amount} required for this coupon',
        }), 400

    already_used = CouponUsage.query.filter_by(
        offer_id=offer.id, user_id=current_user.id
    ).first()
    if already_used:
        return jsonify({'success': False, 'message': 'You have already used this coupon'}), 400

    if offer.discount_type == 'percentage':
        discount = cart_total * (offer.discount_value / 100)
    else:
        discount = offer.discount_value

    if offer.max_discount:
        discount = min(discount, offer.max_discount)

    return jsonify({
        'success':        True,
        'message':        f'Coupon applied! You save ₹{discount:.2f}',
        'discount':       round(discount, 2),
        'discount_type':  offer.discount_type,
        'discount_value': offer.discount_value,
        'code':           offer.code,
    })


@api_bp.route('/api/coupon/validate', methods=['POST'])
@login_required
def api_coupon_validate():
    """Alias for /api/coupon/apply — used by the checkout page."""
    data = request.get_json() or {}
    if 'subtotal' in data and 'cart_total' not in data:
        data['cart_total'] = data['subtotal']
    code       = (data.get('code') or '').strip().upper()
    cart_total = float(data.get('cart_total', 0))

    if not code:
        return jsonify({'success': False, 'message': 'Coupon code required'}), 400
    offer = Offer.query.filter_by(code=code).first()
    if not offer:
        return jsonify({'success': False, 'message': 'Invalid coupon code'}), 404
    valid, msg = offer.is_valid()
    if not valid:
        return jsonify({'success': False, 'message': msg}), 400
    if cart_total < offer.min_order_amount:
        return jsonify({'success': False, 'message': f'Min order ₹{offer.min_order_amount:.0f} required'}), 400
    already_used = CouponUsage.query.filter_by(offer_id=offer.id, user_id=current_user.id).first()
    if already_used:
        return jsonify({'success': False, 'message': 'You have already used this coupon'}), 400
    if offer.discount_type == 'percentage':
        discount = cart_total * (offer.discount_value / 100)
    else:
        discount = offer.discount_value
    if offer.max_discount:
        discount = min(discount, offer.max_discount)
    return jsonify({'success': True, 'discount': round(discount, 2),
                    'message': f'Coupon applied! You save ₹{discount:.2f}'})


# ─────────────────────────────────────────────────────────────────────────────
# ADDRESS APIs
# ─────────────────────────────────────────────────────────────────────────────
@api_bp.route('/api/address/add', methods=['POST'])
@login_required
def api_address_add():
    data = request.get_json() or {}
    try:
        if data.get('is_default'):
            Address.query.filter_by(user_id=current_user.id, is_default=True)\
                .update({'is_default': False})

        addr = Address(
            user_id=current_user.id,
            label=data.get('label', 'Home'),
            full_address=data.get('full_address', ''),
            city=data.get('city'),
            state=data.get('state'),
            pincode=data.get('pincode'),
            landmark=data.get('landmark'),
            is_default=bool(data.get('is_default', False)),
        )
        db.session.add(addr)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Address saved', 'id': addr.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/api/address/<int:address_id>', methods=['DELETE'])
@login_required
def api_address_delete(address_id):
    addr = Address.query.filter_by(id=address_id, user_id=current_user.id).first()
    if not addr:
        return jsonify({'success': False, 'message': 'Address not found'}), 404
    db.session.delete(addr)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Address deleted'})


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH APIs
# ─────────────────────────────────────────────────────────────────────────────
@api_bp.route('/api/home-search')
def api_home_search():
    """Global search: restaurants + dishes + blogs simultaneously."""
    raw_query = request.args.get('q', '').strip()

    if len(raw_query) < 2:
        return jsonify({
            'success': False,
            'message': 'Please enter at least 2 characters',
            'restaurants': [], 'dishes': [], 'blogs': []
        }), 400

    like = f'%{raw_query}%'

    rest_rows = Restaurant.query.filter(
        Restaurant.is_active == True,
        db.or_(
            Restaurant.name.ilike(like),
            Restaurant.cuisine_type.ilike(like),
            Restaurant.location.ilike(like),
            Restaurant.description.ilike(like),
        )
    ).order_by(Restaurant.rating.desc()).limit(6).all()

    restaurants = [{
        'id':            r.id,
        'name':          r.name,
        'cuisine':       r.cuisine_type or '',
        'location':      r.location or '',
        'rating':        float(r.rating) if r.rating else 0.0,
        'image':         r.image or '',
        'delivery_time': r.delivery_time or '',
        'url':           url_for('public.restaurant_menu', restaurant_id=r.id),
    } for r in rest_rows]

    dish_rows = FoodItem.query.filter(
        FoodItem.is_available == True,
        db.or_(
            FoodItem.name.ilike(like),
            FoodItem.description.ilike(like),
            FoodItem.category.ilike(like),
        )
    ).limit(6).all()

    dishes = [{
        'id':              d.id,
        'name':            d.name,
        'price':           float(d.price) if d.price else 0.0,
        'category':        d.category or '',
        'restaurant_id':   d.restaurant_id,
        'restaurant_name': d.restaurant.name if d.restaurant else '',
        'image':           d.image or '',
        'url':             url_for('public.restaurant_menu', restaurant_id=d.restaurant_id),
    } for d in dish_rows]

    blog_rows = Blog.query.filter(
        Blog.status == 'published',
        db.or_(
            Blog.title.ilike(like),
            Blog.content.ilike(like),
            Blog.excerpt.ilike(like),
        )
    ).order_by(Blog.created_at.desc()).limit(4).all()

    blogs = [{
        'id':      b.id,
        'title':   b.title,
        'author':  b.author or 'GrabBite Team',
        'excerpt': b.excerpt or (b.content[:120] + '…') if b.content else '',
        'image':   b.image or '',
        'url':     url_for('public.blog_detail', blog_id=b.id),
    } for b in blog_rows]

    total = len(restaurants) + len(dishes) + len(blogs)

    return jsonify({
        'success':     True,
        'query':       raw_query,
        'total':       total,
        'restaurants': restaurants,
        'dishes':      dishes,
        'blogs':       blogs,
    })


@api_bp.route('/api/search')
def api_search():
    from blueprints.public import _DISHES  # static dish catalogue lives there

    query       = ' '.join(request.args.get('q', '').split())
    search_type = request.args.get('type', 'all')
    per_page    = request.args.get('per_page', 10, type=int)

    if len(query) < 2:
        return jsonify({'success': False, 'message': 'Min 2 characters required', 'results': []}), 400

    if search_type not in ('all', 'restaurants', 'food', 'blogs'):
        search_type = 'all'

    per_page = max(1, min(per_page, 50))
    results  = []

    if search_type in ('all', 'restaurants'):
        restaurants = Restaurant.query.filter(
            db.or_(
                Restaurant.name.ilike(f'%{query}%'),
                Restaurant.cuisine_type.ilike(f'%{query}%'),
                Restaurant.location.ilike(f'%{query}%'),
                Restaurant.description.ilike(f'%{query}%'),
            ),
            Restaurant.is_active == True,
        ).limit(per_page).all()

        for r in restaurants:
            results.append({
                'type':          'restaurant',
                'id':            r.id,
                'name':          r.name,
                'cuisine':       r.cuisine_type,
                'location':      r.location,
                'rating':        r.rating,
                'image':         r.image,
                'delivery_time': r.delivery_time,
                'min_order':     r.min_order,
                'delivery_fee':  r.delivery_fee,
                'url':           url_for('public.restaurant_menu', restaurant_id=r.id),
            })

    if search_type in ('all', 'food'):
        food_items = FoodItem.query.filter(
            db.or_(
                FoodItem.name.ilike(f'%{query}%'),
                FoodItem.description.ilike(f'%{query}%'),
                FoodItem.category.ilike(f'%{query}%'),
            ),
            FoodItem.is_available == True,
        ).limit(per_page).all()

        for item in food_items:
            results.append({
                'type':            'food',
                'id':              item.id,
                'name':            item.name,
                'restaurant_id':   item.restaurant_id,
                'restaurant_name': item.restaurant.name if item.restaurant else '',
                'price':           float(item.price),
                'image':           item.image,
                'category':        item.category,
                'is_available':    item.is_available,
                'url':             url_for('public.restaurant_menu', restaurant_id=item.restaurant_id),
            })

        existing_food_names = {
            item.get('name', '').strip().lower()
            for item in results
            if item.get('type') == 'food'
        }
        query_lower = query.lower()
        for dish in _DISHES.values():
            tags_val  = dish.get('tags')
            tags_list: list[str] = ([t for t in tags_val] if isinstance(tags_val, list)
                                     else ([cast(str, tags_val)] if tags_val is not None else []))
            haystack  = ' '.join([
                str(dish.get('name', '')),
                str(dish.get('category', '')),
                str(dish.get('restaurant', '')),
                str(dish.get('desc', '')),
                str(dish.get('details', '')),
                ' '.join(tags_list),
            ]).lower()
            dish_name = str(dish.get('name', '')).strip()
            if query_lower not in haystack or dish_name.lower() in existing_food_names:
                continue
            results.append({
                'type':            'food',
                'id':              dish.get('id'),
                'name':            dish_name,
                'restaurant_id':   '',
                'restaurant_name': dish.get('restaurant', ''),
                'price':           float(dish.get('price') or 0),
                'image':           dish.get('image', ''),
                'category':        dish.get('category', ''),
                'is_available':    True,
                'url':             url_for('public.dish_detail', dish_id=dish.get('id')),
            })

    if search_type in ('all', 'blogs'):
        blogs = Blog.query.filter(
            db.or_(
                Blog.title.ilike(f'%{query}%'),
                Blog.content.ilike(f'%{query}%'),
                Blog.excerpt.ilike(f'%{query}%'),
            ),
            Blog.status == 'published',
        ).limit(per_page).all()

        for b in blogs:
            results.append({
                'type':    'blog',
                'id':      b.id,
                'title':   b.title,
                'excerpt': b.excerpt or (b.content[:150] + '...') if b.content else '',
                'author':  b.author,
                'image':   b.image,
                'url':     url_for('public.blog_detail', blog_id=b.id),
            })

    results.sort(key=lambda x: (
        0 if query.lower() in x.get('name', x.get('title', '')).lower() else 1,
    ))

    return jsonify({'success': True, 'query': query, 'results': results, 'count': len(results)})


@api_bp.route('/api/search/suggestions')
def api_search_suggestions():
    query = ' '.join(request.args.get('q', '').split())
    limit = request.args.get('limit', 5, type=int)

    if len(query) < 2:
        return jsonify({'success': False, 'suggestions': []}), 400

    suggestions = []

    restaurants = Restaurant.query.filter(
        Restaurant.name.ilike(f'%{query}%'), Restaurant.is_active == True
    ).limit(limit).all()
    for r in restaurants:
        suggestions.append({'type': 'restaurant', 'text': r.name, 'value': r.name})

    food_items = FoodItem.query.filter(
        FoodItem.name.ilike(f'%{query}%'), FoodItem.is_available == True
    ).limit(max(0, limit - len(suggestions))).all()
    for f in food_items:
        suggestions.append({'type': 'food', 'text': f.name, 'value': f.name})

    return jsonify({'success': True, 'suggestions': suggestions[:limit]})


@api_bp.route('/api/restaurants/search')
def search_restaurants():
    query = request.args.get('q', '').lower()
    qs = Restaurant.query.filter(Restaurant.is_active == True)
    if query:
        search = f'%{query}%'
        qs = qs.filter(db.or_(
            Restaurant.name.ilike(search),
            Restaurant.location.ilike(search),
            Restaurant.description.ilike(search),
        ))
    rests = qs.all()
    return jsonify([{
        'id': r.id, 'name': r.name, 'location': r.location,
        'rating': r.rating, 'description': r.description, 'image': r.image,
    } for r in rests])


# ─────────────────────────────────────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────────────────────────────────────
@api_bp.route('/api/review', methods=['POST'])
@api_bp.route('/api/reviews/add', methods=['POST'])
@login_required
def add_review():
    try:
        data          = request.get_json() or {}
        restaurant_id = data.get('restaurant_id')
        rating        = data.get('rating')
        comment       = (data.get('comment') or '').strip()

        if not restaurant_id or not rating:
            return jsonify({'success': False, 'message': 'restaurant_id and rating required'}), 400
        if not (1 <= int(rating) <= 5):
            return jsonify({'success': False, 'message': 'Rating must be 1–5'}), 400

        restaurant = Restaurant.query.get(restaurant_id)
        if not restaurant:
            return jsonify({'success': False, 'message': 'Restaurant not found'}), 404

        existing = Review.query.filter_by(
            user_id=current_user.id, restaurant_id=restaurant_id
        ).first()

        if existing:
            existing.rating     = int(rating)
            existing.comment    = comment
            existing.created_at = datetime.now(timezone.utc)
        else:
            review = Review(
                user_id=current_user.id,
                restaurant_id=restaurant_id,
                rating=int(rating),
                comment=comment,
            )
            db.session.add(review)

        db.session.commit()
        _update_restaurant_rating(restaurant_id)

        return jsonify({'success': True, 'message': 'Review submitted!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route('/api/reviews/restaurant/<int:restaurant_id>')
def get_restaurant_reviews(restaurant_id):
    page     = request.args.get('page', 1, type=int)
    per_page = 10

    reviews = db.session.query(Review, User)\
        .join(User, Review.user_id == User.id)\
        .filter(Review.restaurant_id == restaurant_id)\
        .order_by(Review.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success':  True,
        'reviews':  [{
            'id':         rv.id,
            'rating':     rv.rating,
            'comment':    rv.comment,
            'created_at': rv.created_at.strftime('%B %d, %Y'),
            'user_name':  u.name,
        } for rv, u in reviews.items],
        'has_next': reviews.has_next,
        'has_prev': reviews.has_prev,
        'total':    reviews.total,
    })


def _update_restaurant_rating(restaurant_id):
    """Recalculate and persist average rating for a restaurant."""
    try:
        reviews = Review.query.filter_by(restaurant_id=restaurant_id).all()
        if reviews:
            avg = sum(r.rating for r in reviews) / len(reviews)
            restaurant = Restaurant.query.get(restaurant_id)
            if restaurant:
                restaurant.rating        = round(avg, 1)
                restaurant.total_reviews = len(reviews)
                db.session.commit()
    except Exception as e:
        current_app.logger.error(f'_update_restaurant_rating error: {e}')


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS API
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# NEWSLETTER & FOOTER APIs
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
