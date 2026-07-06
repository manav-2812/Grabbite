"""
Grabbite — Admin: Dashboard
/admin/dashboard, /admin/api/stats/*, /admin/api/analytics
"""
from datetime import datetime, timedelta, timezone

from flask import render_template, jsonify
from flask_login import login_required

from db import db
from models import User, Restaurant, FoodItem, Blog, Order, Offer, AdminActivity
from blueprints.admin import admin
from utils.decorators import admin_required


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

    revenue_result = db.session.query(db.func.sum(Order.total_amount))\
        .filter(Order.status == 'delivered').scalar()
    total_revenue = float(revenue_result or 0)

    recent_activities = AdminActivity.query.order_by(
        AdminActivity.created_at.desc()
    ).limit(10).all()

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

        daily_orders  = []
        daily_revenue = []
        for i in range(7):
            day   = start_date + timedelta(days=i)
            label = day.strftime('%a')
            cnt   = Order.query.filter(db.func.date(Order.created_at) == day).count()
            rev   = db.session.query(
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
            'daily_orders':    daily_orders,
            'daily_revenue':   daily_revenue,
            'top_restaurants': top_restaurants,
            'customer_count':  customer_count,
            'owner_count':     owner_count,
            'admin_count':     admin_count,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
