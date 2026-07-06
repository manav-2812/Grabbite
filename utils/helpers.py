"""
Grabbite Utility Helpers
Shared template globals and utility functions.
"""
import os
from urllib.parse import urlparse
from flask import current_app


# H3 fix: the DB stores legacy defaults with underscores ('food_default.jpg') but the
# on-disk assets were renamed to dashes ('food-default.jpg'). Translate them.
_UNDERSCORE_TO_DASH = {
    'food_default.jpg':       'food-default.jpg',
    'restaurant_default.jpg': 'restaurant-default.jpg',
    'blog_default.jpg':       'blog-default.jpg',
    'default.jpg':            'placeholder-food.jpg',
}


def safe_next_url(next_page):
    """Return next_page only if it is a safe same-origin relative URL.

    CRIT-3 fix: rejects absolute URLs (http://evil.com, //evil.com, javascript:,
    data:, etc.) to prevent open-redirect phishing attacks via ?next= parameters.
    Only relative paths starting with a single '/' (and not '//') are allowed.

    Usage:
        from utils.helpers import safe_next_url
        target = safe_next_url(request.args.get('next'))
        if target:
            return redirect(target)
    """
    if not next_page or not isinstance(next_page, str):
        return None
    # Must be a relative path: starts with '/' but NOT '//' (protocol-relative).
    if not next_page.startswith('/') or next_page.startswith('//'):
        return None
    # Reject any URL with a scheme or authority (defence in depth).
    parsed = urlparse(next_page)
    if parsed.scheme or parsed.netloc:
        return None
    return next_page


def food_image_url(image_field: str) -> str:
    """
    Return a safe, absolute URL for a food image field.

    Priority:
      1. If the field starts with http(s), return as-is.
      2. Translate legacy underscore defaults to dash-named assets.
      3. If a file exists at static/uploads/<field>, return that path.
      4. If a file exists at static/img/<candidate>, return that path.
      5. If a file exists at static/img/<field>, return that path.
      6. Fall back to the dash variant (or placeholder-food.jpg).
    """
    if not image_field:
        return '/static/img/placeholder-food.jpg'

    field = image_field.strip()

    if field.startswith(('http://', 'https://')):
        return field

    candidate = _UNDERSCORE_TO_DASH.get(field, field)

    static_folder = current_app.static_folder or ''

    # Check uploads dir
    upload_path = os.path.join(static_folder, 'uploads', field)
    if os.path.exists(upload_path):
        return f'/static/uploads/{field}'

    # Check static/img for the dash-renamed asset first
    img_dir = os.path.join(static_folder, 'img')
    if os.path.exists(os.path.join(img_dir, candidate)):
        return f'/static/img/{candidate}'
    if os.path.exists(os.path.join(img_dir, field)):
        return f'/static/img/{field}'

    # Final fallback: dash variant (browser sees 404 if missing, but the
    # templates have onerror handlers that swap in the placeholder).
    return f'/static/img/{candidate}'


def format_currency(amount: float, symbol: str = '₹') -> str:
    """Format a float as an Indian Rupee string."""
    return f'{symbol}{amount:,.2f}'


def _update_restaurant_rating(restaurant_id: int) -> None:
    """Recalculate and persist the average rating for a restaurant.

    Extracted from app.py (Plan 2 refactor). Safe to call from any blueprint
    or utility that has an active app context.
    """
    from models import Review, Restaurant
    from db import db
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


def register_template_globals(app):
    """Register all helpers as Jinja2 globals so every template can use them."""
    app.jinja_env.globals['food_image_url']    = food_image_url
    app.jinja_env.globals['format_currency']   = format_currency
