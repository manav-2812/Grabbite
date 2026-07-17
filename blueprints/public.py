"""
Grabbite — Public Blueprint
Handles all publicly-accessible pages and user-facing pages (not admin/owner).

Plan 4 refactor: static data blobs (_static_offers, _DISHES) moved to
utils/page_builders.py (~420 lines extracted). This file is now routes-only.
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, abort, current_app)
from flask_login import current_user, login_required
from collections import OrderedDict

from db import db
from models import (Restaurant, FoodItem, Blog, Notification, Offer,
                    Wishlist, Review)
from utils.page_builders import _static_offers, _DISHES

public_bp = Blueprint('public', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/')
def index():
    from utils.image_data import food_photo as _food_photo  # moved from app.py in Plan 2 refactor
    categories = [
        ('Pizza', 'fa-pizza-slice'), ('Burger', 'fa-burger'), ('Biryani', 'fa-bowl-rice'),
        ('Chinese', 'fa-bowl-food'), ('Momos', 'fa-utensils'), ('South Indian', 'fa-leaf'),
        ('North Indian', 'fa-pepper-hot'), ('Desserts', 'fa-ice-cream'), ('Beverages', 'fa-mug-hot'),
        ('Sandwiches', 'fa-bread-slice'), ('Rolls', 'fa-scroll'), ('Pasta', 'fa-utensils'),
        ('Ice Cream', 'fa-snowflake'), ('Healthy Food', 'fa-seedling'), ('Fast Food', 'fa-bolt'),
        ('Street Food', 'fa-hotdog'), ('Coffee', 'fa-coffee'), ('Bakery', 'fa-cookie-bite'),
        ('Seafood', 'fa-fish'), ('Vegan', 'fa-carrot'),
    ]
    category_cards = [{
        'name': name,
        'icon': icon,
        'image': _food_photo(f'category-{idx}', name.replace(' ', '+'), 480, 360),
        'url': url_for('public.search_page', q=name, type='all'),
    } for idx, (name, icon) in enumerate(categories, 1)]

    top_restaurants = Restaurant.query.filter_by(is_active=True)\
        .order_by(Restaurant.rating.desc(), Restaurant.id.desc()).limit(8).all()
    trending_dishes = FoodItem.query.filter_by(is_available=True)\
        .order_by(FoodItem.is_bestseller.desc(), FoodItem.rating.desc(), FoodItem.id.desc()).limit(10).all()
    latest_blogs = Blog.query.filter_by(status='published')\
        .order_by(Blog.created_at.desc(), Blog.id.desc()).limit(4).all()

    offers = [
        {'title': 'Flat 50% OFF', 'copy': 'On first GrabBite orders above ₹299', 'code': 'WELCOME50',
         'image': _food_photo('offer-1', 'pizza+deal', 1000, 520), 'url': url_for('public.restaurants')},
        {'title': 'Biryani Festival', 'copy': 'Royal dum biryanis from top brands', 'code': 'DUMLOVE',
         'image': _food_photo('offer-2', 'biryani', 1000, 520), 'url': url_for('public.restaurants', q='Biryani')},
        {'title': 'Healthy Week', 'copy': 'Bowls, salads and subs under ₹349', 'code': 'FITBITE',
         'image': _food_photo('offer-3', 'healthy+salad', 1000, 520), 'url': url_for('public.restaurants', q='Healthy Food')},
    ]
    collections = [
        {'title': 'Date Night Picks', 'count': '18 places', 'image': _food_photo('collection-1', 'dinner', 720, 520), 'url': url_for('public.restaurants', sort='rating_desc')},
        {'title': 'Under 30 Minutes', 'count': '24 fast kitchens', 'image': _food_photo('collection-2', 'delivery', 720, 520), 'url': url_for('public.restaurants', sort='delivery_time')},
        {'title': 'Premium Biryani Houses', 'count': '11 royal menus', 'image': _food_photo('collection-3', 'biryani', 720, 520), 'url': url_for('public.restaurants', q='Biryani')},
        {'title': 'Sweet Tooth Trail', 'count': '15 dessert stops', 'image': _food_photo('collection-4', 'dessert', 720, 520), 'url': url_for('public.restaurants', q='Desserts')},
    ]
    best_cuisines = [
        {'name': name, 'url': url_for('public.search_page', q=name, type='all')}
        for name in ['Italian', 'American', 'Mughlai', 'Chinese', 'South Indian', 'Healthy Food', 'Desserts', 'Coffee']
    ]
    reviews = [
        ('Aarav Mehta', 'The new search found KFC, biryani and dessert options instantly. Super polished!', 5),
        ('Nisha Rao', 'Cards feel premium and the offers are easy to scan on mobile.', 5),
        ('Kabir Sethi', 'Loved the collection sliders and fast restaurant discovery.', 4),
        ('Meera Iyer', 'GrabBite makes weekday dinners ridiculously simple.', 5),
        ('Rohan Kapoor', 'The dish cards with veg labels and delivery time are very helpful.', 4),
        ('Fatima Khan', 'Best biryani selection I have seen in one place.', 5),
        ('Dev Malhotra', 'Smooth animations without feeling heavy.', 5),
        ('Ananya Das', 'The category filters actually take me to relevant food.', 4),
        ('Ishaan Gupta', 'Looks and feels like a modern delivery app now.', 5),
    ]

    return render_template(
        'index.html',
        categories=category_cards,
        top_restaurants=top_restaurants,
        trending_dishes=trending_dishes,
        latest_blogs=latest_blogs,
        offers=offers,
        collections=collections,
        best_cuisines=best_cuisines,
        reviews=reviews,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RESTAURANTS
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/restaurants')
def restaurants():
    search_query = request.args.get('q', '')
    cuisine_type = request.args.get('cuisine', '')
    sort_by      = request.args.get('sort', 'rating_desc')
    page         = request.args.get('page', 1, type=int)
    per_page     = 12

    query = Restaurant.query.filter_by(is_active=True)

    if search_query:
        search = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Restaurant.name.ilike(search),
                Restaurant.location.ilike(search),
                Restaurant.description.ilike(search),
                Restaurant.cuisine_type.ilike(search),
            )
        )

    if cuisine_type:
        terms = [t.strip() for t in cuisine_type.split(',')]
        query = query.filter(db.or_(
            *[Restaurant.cuisine_type.ilike(f'%{t}%') for t in terms]
        ))

    if sort_by == 'rating_asc':
        query = query.order_by(Restaurant.rating.asc())
    elif sort_by == 'delivery_time':
        query = query.order_by(Restaurant.delivery_time.asc())
    elif sort_by == 'min_order':
        query = query.order_by(Restaurant.min_order.asc())
    else:
        query = query.order_by(Restaurant.rating.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    cuisine_types = [c[0] for c in
                     db.session.query(Restaurant.cuisine_type).distinct().all()
                     if c[0]]

    def url_for_other_page(p):
        args = request.args.copy()
        args['page'] = p
        return url_for('public.restaurants', **args)

    return render_template('restaurants.html',
                           restaurants=pagination.items,
                           pagination=pagination,
                           url_for_other_page=url_for_other_page,
                           search_query=search_query,
                           cuisine_types=cuisine_types,
                           active_cuisine=cuisine_type,
                           sort_by=sort_by)


@public_bp.route('/restaurant/<int:restaurant_id>')
def restaurant_menu(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    food_items = FoodItem.query.filter_by(
        restaurant_id=restaurant_id, is_available=True
    ).all()
    reviews = Review.query.filter_by(restaurant_id=restaurant_id)\
        .order_by(Review.created_at.desc()).all()

    is_wishlisted = False
    if current_user.is_authenticated:
        is_wishlisted = Wishlist.query.filter_by(
            user_id=current_user.id, restaurant_id=restaurant_id
        ).first() is not None

    return render_template('restaurant_menu.html',
                           restaurant=restaurant,
                           food_items=food_items,
                           reviews=reviews,
                           is_wishlisted=is_wishlisted)


# ─────────────────────────────────────────────────────────────────────────────
# BLOGS
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/blogs')
def blogs():
    category = request.args.get('category')
    q = Blog.query.filter_by(status='published')
    if category:
        q = q.filter_by(category=category)
    blog_list = q.order_by(Blog.created_at.desc()).all()
    return render_template('blogs.html', blogs=blog_list)


@public_bp.route('/blog/<int:blog_id>')
def blog_detail(blog_id):
    blog = Blog.query.get_or_404(blog_id)
    from sqlalchemy import update as _sa_update_blog_views
    db.session.execute(
        _sa_update_blog_views(Blog)
        .where(Blog.id == blog_id)
        .values(views=(Blog.views or 0) + 1)
    )
    db.session.commit()
    db.session.refresh(blog)

    related_blogs = Blog.query.filter(
        Blog.category == blog.category,
        Blog.id != blog_id,
        Blog.status == 'published',
    ).order_by(Blog.created_at.desc()).limit(3).all()

    prev_blog = Blog.query.filter(Blog.id < blog_id, Blog.status == 'published')\
        .order_by(Blog.id.desc()).first()
    next_blog = Blog.query.filter(Blog.id > blog_id, Blog.status == 'published')\
        .order_by(Blog.id.asc()).first()

    return render_template('blog_detail.html',
                           blog=blog,
                           related_blogs=related_blogs,
                           prev_blog=prev_blog,
                           next_blog=next_blog)


# ─────────────────────────────────────────────────────────────────────────────
# GALLERY
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/gallery')
def gallery():
    categories_order = [
        'Curries & Mains', 'Rice & Biryani', 'South Indian', 'Snacks & Street Food',
        'Non-Veg Specials', 'Sweets & Desserts', 'Cakes & Bakery',
        'Drinks & Beverages', 'Breakfast', 'Fast Food & Chinese',
    ]
    cat_icons = {
        'Curries & Mains':      ('fa-fire',          '#e53935'),
        'Rice & Biryani':       ('fa-bowl-rice',     '#f59e0b'),
        'South Indian':         ('fa-leaf',           '#10b981'),
        'Snacks & Street Food': ('fa-hotdog',         '#8b5cf6'),
        'Non-Veg Specials':     ('fa-drumstick-bite', '#ef4444'),
        'Sweets & Desserts':    ('fa-candy-cane',     '#ec4899'),
        'Cakes & Bakery':       ('fa-birthday-cake',  '#6366f1'),
        'Drinks & Beverages':   ('fa-glass-water',    '#0ea5e9'),
        'Breakfast':            ('fa-sun',            '#f97316'),
        'Fast Food & Chinese':  ('fa-burger',         '#14b8a6'),
    }
    grouped = OrderedDict()
    for cat in categories_order:
        icon, color = cat_icons.get(cat, ('fa-utensils', '#e53935'))
        dishes_in_cat = [d for d in _DISHES.values() if d.get('category') == cat]
        grouped[cat] = {'icon': icon, 'color': color, 'dishes': dishes_in_cat}

    total = len(_DISHES)
    return render_template('gallery.html', grouped=grouped, total=total)


@public_bp.route('/dish/<int:dish_id>')
def dish_detail(dish_id):
    dish = _DISHES.get(dish_id)
    if not dish:
        abort(404)
    same_cat = [d for d in _DISHES.values() if d['id'] != dish_id and d.get('category') == dish.get('category')]
    others   = [d for d in _DISHES.values() if d['id'] != dish_id and d.get('category') != dish.get('category')]
    related  = (same_cat + others)[:4]
    return render_template('dish_detail.html', dish=dish, related=related)


# ─────────────────────────────────────────────────────────────────────────────
# STATIC PAGES
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/about')
def about():
    return render_template('about.html')


@public_bp.route('/careers')
def careers():
    return render_template('careers.html')


@public_bp.route('/help')
def help():
    return render_template('help.html')


@public_bp.route('/search')
def search_page():
    query       = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    return render_template('search.html', query=query, search_type=search_type)


# ─────────────────────────────────────────────────────────────────────────────
# OFFERS
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/offer/<int:offer_id>')
def offer_details(offer_id):
    offer = _static_offers.get(offer_id)
    if not offer:
        abort(404)
    return render_template('offer_details.html', offer=offer)


# ─────────────────────────────────────────────────────────────────────────────
# WISHLIST PAGE (user-facing, not the API)
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id)\
        .join(Restaurant, Wishlist.restaurant_id == Restaurant.id).all()
    return render_template('wishlist.html', wishlist_items=items)


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS PAGE
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/notifications')
@login_required
def notifications_page():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(100).all()
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    return render_template('notifications.html', notifications=notifs)


# ─────────────────────────────────────────────────────────────────────────────
# SEO / CRAWLER
# ─────────────────────────────────────────────────────────────────────────────
@public_bp.route('/robots.txt')
def robots_txt():
    from flask import send_from_directory
    return send_from_directory(current_app.static_folder, 'robots.txt',
                               mimetype='text/plain')


@public_bp.route('/sitemap.xml')
def sitemap_xml():
    import xml.etree.ElementTree as ET
    from flask import make_response
    
    base_url = request.url_root.rstrip('/')
    
    # Static pages
    pages = [
        {'loc': f"{base_url}/", 'changefreq': 'daily', 'priority': '1.0'},
        {'loc': f"{base_url}/restaurants", 'changefreq': 'daily', 'priority': '0.9'},
        {'loc': f"{base_url}/gallery", 'changefreq': 'weekly', 'priority': '0.8'},
        {'loc': f"{base_url}/blogs", 'changefreq': 'weekly', 'priority': '0.7'},
        {'loc': f"{base_url}/about", 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': f"{base_url}/careers", 'changefreq': 'monthly', 'priority': '0.5'},
        {'loc': f"{base_url}/help", 'changefreq': 'monthly', 'priority': '0.5'},
    ]
    
    # Dynamic restaurants
    try:
        restaurants = Restaurant.query.filter_by(is_active=True).all()
        for r in restaurants:
            pages.append({
                'loc': f"{base_url}/restaurant/{r.id}",
                'changefreq': 'weekly',
                'priority': '0.8'
            })
    except Exception:
        pass
        
    # Dynamic blogs
    try:
        blogs = Blog.query.filter_by(status='published').all()
        for b in blogs:
            pages.append({
                'loc': f"{base_url}/blog/{b.id}",
                'changefreq': 'monthly',
                'priority': '0.6'
            })
    except Exception:
        pass
        
    # Dynamic dishes
    try:
        dishes = FoodItem.query.filter_by(is_available=True).all()
        for d in dishes:
            pages.append({
                'loc': f"{base_url}/dish/{d.id}",
                'changefreq': 'weekly',
                'priority': '0.6'
            })
    except Exception:
        pass

    # Build XML
    urlset = ET.Element('urlset', xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for page in pages:
        url = ET.SubElement(urlset, 'url')
        loc = ET.SubElement(url, 'loc')
        loc.text = page['loc']
        
        changefreq = ET.SubElement(url, 'changefreq')
        changefreq.text = page['changefreq']
        
        priority = ET.SubElement(url, 'priority')
        priority.text = page['priority']
        
    xml_str = ET.tostring(urlset, encoding='utf-8', method='xml')
    response = make_response(b'<?xml version="1.0" encoding="utf-8"?>\n' + xml_str)
    response.headers['Content-Type'] = 'application/xml'
    return response

