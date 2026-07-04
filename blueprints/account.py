"""
Grabbite — Account Blueprint
HIGH-4: Extracted from app.py as part of the blueprint refactor.
Handles authentication (login, signup, logout, password reset) and
user-facing account management (profile, orders, cart, checkout, address).
"""
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, make_response, current_app)
from flask_login import current_user, login_required, logout_user
from werkzeug.security import generate_password_hash
from itsdangerous import URLSafeTimedSerializer as _Serializer, SignatureExpired, BadSignature

from db import db
from models import (User, Order, Cart, FoodItem, Restaurant, Address)

account_bp = Blueprint('account', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN HELPERS (password reset)
# ─────────────────────────────────────────────────────────────────────────────
def _generate_reset_token(email: str) -> str:
    s = _Serializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt=current_app.config['RESET_TOKEN_SALT'])


def _verify_reset_token(token: str, max_age_seconds: int = 1800):
    s = _Serializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt=current_app.config['RESET_TOKEN_SALT'], max_age=max_age_seconds)
        return email
    except (SignatureExpired, BadSignature):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────
@account_bp.route('/login', methods=['GET'])
def login():
    if current_user.is_authenticated:
        if current_user.is_administrator():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('public.index'))
    return render_template('login.html')


@account_bp.route('/login', methods=['POST'])
def login_post_route():
    from auth_routes import login_post
    return login_post()


@account_bp.route('/signup', methods=['GET'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))
    return render_template('signup.html')


@account_bp.route('/signup', methods=['POST'])
def signup_post_route():
    from auth_routes import signup_post
    return signup_post()


@account_bp.route('/signup/restaurant', methods=['GET'])
def signup_owner():
    if current_user.is_authenticated:
        if current_user.is_restaurant_owner():
            return redirect(url_for('owner.dashboard'))
        return redirect(url_for('public.index'))
    return render_template('signup_owner.html')


@account_bp.route('/signup/restaurant', methods=['POST'])
def signup_owner_post_route():
    from auth_routes import signup_owner_post
    return signup_owner_post()


@account_bp.route('/logout')
def logout_route():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('public.index'))


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET
# ─────────────────────────────────────────────────────────────────────────────
@account_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """GET → show form. POST → send reset email if user exists."""
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect(url_for('account.forgot_password'))

        user = User.query.filter_by(email=email).first()

        if user and user.is_active:
            token = _generate_reset_token(user.email)
            from utils.mail import send_password_reset_email
            sent = send_password_reset_email(user, token)
            if not sent:
                current_app.logger.warning(
                    f'Password reset email not sent for {email} — '
                    'MAIL_SERVER may not be configured.'
                )

        flash(
            'If an account exists for that email, a password reset link has been sent. '
            'Please check your inbox (and spam folder).',
            'success',
        )
        return redirect(url_for('account.forgot_password'))

    return render_template('forgot_password.html')


@account_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def forgot_password_reset(token: str):
    """Verify the signed token, then let the user set a new password."""
    if current_user.is_authenticated:
        return redirect(url_for('public.index'))

    email = _verify_reset_token(token)

    if request.method == 'GET':
        expired = email is None
        return render_template('reset_password.html', token=token, expired=expired)

    # POST — change password
    if email is None:
        flash('This password reset link has expired or is invalid. Please request a new one.', 'error')
        return redirect(url_for('account.forgot_password'))

    password = request.form.get('password', '')
    confirm  = request.form.get('confirm_password', '')

    if not password or len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return render_template('reset_password.html', token=token, expired=False)

    if password != confirm:
        flash('Passwords do not match.', 'error')
        return render_template('reset_password.html', token=token, expired=False)

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Account not found.', 'error')
        return redirect(url_for('account.login'))

    try:
        user.password = generate_password_hash(password)
        db.session.commit()
        session.clear()
        from utils.mail import send_password_reset_success
        send_password_reset_success(user)
        flash('Your password has been reset successfully! You can now log in.', 'success')
        return redirect(url_for('account.login'))
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f'forgot_password_reset error: {exc}')
        flash('An error occurred. Please try again.', 'error')
        return render_template('reset_password.html', token=token, expired=False)


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────
@account_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    user = User.query.get_or_404(current_user.id)
    user_orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).limit(5).all()
    user_addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('profile.html', user=user,
                           user_orders=user_orders,
                           user_addresses=user_addresses)


@account_bp.route('/profile', methods=['POST'])
@login_required
def profile_update():
    from auth_routes import update_profile
    return update_profile()


# ─────────────────────────────────────────────────────────────────────────────
# ORDERS
# ─────────────────────────────────────────────────────────────────────────────
@account_bp.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)


# ─────────────────────────────────────────────────────────────────────────────
# CART
# ─────────────────────────────────────────────────────────────────────────────
@account_bp.route('/cart')
@login_required
def cart():
    cart_items = db.session.query(Cart, FoodItem, Restaurant)\
        .join(FoodItem, Cart.food_item_id == FoodItem.id)\
        .join(Restaurant, FoodItem.restaurant_id == Restaurant.id)\
        .filter(Cart.user_id == current_user.id)\
        .all()

    subtotal     = sum(c.quantity * f.price for c, f, _ in cart_items)
    tax          = round(subtotal * 0.18, 2)
    delivery_fee = 0.0 if subtotal > 500 else 40.0
    total        = round(subtotal + tax + delivery_fee, 2)

    cart_data = [{
        'cart_id':         c.id,
        'food_id':         f.id,
        'food_name':       f.name,
        'restaurant_name': r.name,
        'restaurant_id':   r.id,
        'price':           float(f.price),
        'quantity':        c.quantity,
        'notes':           c.notes or '',
        'image':           f.image if f.image else 'food_default.jpg',
        'item_total':      float(c.quantity * f.price),
    } for c, f, r in cart_items]

    response = make_response(render_template('cart.html',
        cart_items=cart_items,
        cart_data=cart_data,
        order_summary={
            'subtotal':     subtotal,
            'tax':          tax,
            'delivery_fee': delivery_fee,
            'total':        total,
        },
    ))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma']        = 'no-cache'
    return response


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────
@account_bp.route('/checkout')
@login_required
def checkout():
    cart_items = db.session.query(Cart, FoodItem, Restaurant)\
        .join(FoodItem, Cart.food_item_id == FoodItem.id)\
        .join(Restaurant, FoodItem.restaurant_id == Restaurant.id)\
        .filter(Cart.user_id == current_user.id)\
        .all()

    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('public.restaurants'))

    subtotal     = sum(c.quantity * f.price for c, f, _ in cart_items)
    tax          = round(subtotal * 0.18, 2)
    delivery_fee = 0.0 if subtotal > 500 else 40.0
    total        = round(subtotal + tax + delivery_fee, 2)

    user_addresses = Address.query.filter_by(user_id=current_user.id).all()

    return render_template('checkout.html',
                           cart_items=cart_items,
                           subtotal=subtotal,
                           tax=tax,
                           delivery_fee=delivery_fee,
                           total=total,
                           user_addresses=user_addresses,
                           razorpay_key=current_app.config['RAZORPAY_KEY_ID'])


# ─────────────────────────────────────────────────────────────────────────────
# ADDRESS PAGE
# ─────────────────────────────────────────────────────────────────────────────
@account_bp.route('/address')
@login_required
def address():
    user_addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('address.html', addresses=user_addresses)
