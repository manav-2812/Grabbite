"""
Grabbite — API: Reviews
/api/review (POST), /api/reviews/add (POST), /api/reviews/restaurant/<id>
"""
from datetime import datetime, timezone

from flask import request, jsonify, current_app
from flask_login import current_user, login_required

from db import db
from models import Review, Restaurant, User
from utils.helpers import _update_restaurant_rating
from blueprints.api import api_bp


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
