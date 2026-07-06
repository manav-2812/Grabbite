"""
Grabbite — API: Search
/api/home-search, /api/search, /api/search/suggestions, /api/restaurants/search
"""
from typing import cast

from flask import request, jsonify, url_for
from flask_login import current_user

from db import db
from models import Restaurant, FoodItem, Blog
from blueprints.api import api_bp


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
