"""
Grabbite — API: Wishlist
/api/wishlist/toggle
"""
from flask import request, jsonify
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from db import db
from models import Wishlist, Restaurant
from blueprints.api import api_bp


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
