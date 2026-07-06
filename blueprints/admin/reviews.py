"""
Grabbite — Admin: Reviews Management
/admin/reviews, /admin/api/review/*
"""
from flask import render_template, jsonify
from flask_login import login_required

from db import db
from models import Review
from blueprints.admin import admin
from utils.decorators import admin_required


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
