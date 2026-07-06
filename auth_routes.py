"""
Grabbite — Authentication Routes
Handles login, signup, logout, and profile update for all user roles.
"""
from flask import (Blueprint, request, redirect, url_for, session,
                   flash, jsonify, current_app)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime, timezone
import os
import re
import secrets

from models import User, Notification, db
from utils.uploads import allowed_file, _looks_like_image, resize_image, save_upload

auth = Blueprint('auth', __name__)

# Basic RFC-5322-inspired email regex — catches most typos without a library dep
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')



# ─────────────────────────────────────────────────────────────────────────────
# WELCOME NOTIFICATION SEEDER
# ─────────────────────────────────────────────────────────────────────────────
# LOW-4 note: these 3 strings are intentional welcome copy, not dead code.
# They are consumed by _seed_welcome_notifications() below on every new signup.
# If the copy ever grows beyond ~10 items, move to instance/welcome_seeds.json.
_WELCOME_SEEDS = [
    {
        'title':   'Welcome to GrabBite!',
        'message': 'Thanks for joining! Explore restaurants near you and enjoy your first order.',
        'type':    'general',
        'link':    '/restaurants',
    },
    {
        'title':   'Special Offer: 20% OFF',
        'message': 'Use code GRAB20 on your next order to get 20% off (max ₹200 discount).',
        'type':    'promo',
        'link':    '/restaurants',
    },
    {
        'title':   'Your Order Journey Starts Here',
        'message': 'Place your first order and track it live. Fast delivery guaranteed!',
        'type':    'order',
        'link':    '/orders',
    },
]

def _seed_welcome_notifications(user_id: int) -> None:
    """Create welcome notifications for a user if they don't already exist."""
    try:
        for s in _WELCOME_SEEDS:
            exists = Notification.query.filter_by(
                user_id=user_id, title=s['title']
            ).first()
            if not exists:
                db.session.add(Notification(user_id=user_id, **s))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.warning(f'_seed_welcome_notifications failed: {exc}')


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN (POST) — called from app.py via login_post_route proxy
# Do NOT add @auth.route here — app.py owns the /login POST route to avoid
# Werkzeug routing conflict (both registering at the same URL).
# ─────────────────────────────────────────────────────────────────────────────
def login_post():
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    remember = bool(request.form.get('remember'))

    if not email or not password:
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('account.login'))

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        flash('Invalid email or password. Please try again.', 'error')
        return redirect(url_for('account.login'))

    if not user.is_active:
        flash('Your account has been deactivated. Please contact support.', 'error')
        return redirect(url_for('account.login'))

    login_user(user, remember=remember)
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    # Seed welcome notifications for first-time users
    _seed_welcome_notifications(user.id)

    flash(f'Welcome back, {user.name}!', 'success')

    # CRIT-3 fix: validate the ?next= parameter is a same-origin URL before redirecting.
    # An attacker-controlled ?next=https://evil.com enables phishing via a trusted origin.
    # safe_next_url lives in utils.helpers so any blueprint can reuse it.
    from utils.helpers import safe_next_url
    next_page = safe_next_url(request.args.get('next'))
    if next_page:
        return redirect(next_page)
    if user.is_administrator():
        return redirect(url_for('admin.dashboard'))
    if user.is_restaurant_owner():
        return redirect(url_for('owner.dashboard'))
    return redirect(url_for('public.index'))


# ─────────────────────────────────────────────────────────────────────────────
# SIGNUP (POST)
# ─────────────────────────────────────────────────────────────────────────────
def signup_post():
    name             = request.form.get('name', '').strip()
    email            = request.form.get('email', '').strip().lower()
    contact          = request.form.get('contact', '').strip()
    address          = request.form.get('address', '').strip()
    password         = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Validation
    if not all([name, email, password, confirm_password]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('account.signup'))

    if len(name) < 2:
        flash('Name must be at least 2 characters.', 'error')
        return redirect(url_for('account.signup'))

    if not _EMAIL_RE.match(email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('account.signup'))

    if len(password) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('account.signup'))

    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('account.signup'))

    if User.query.filter_by(email=email).first():
        flash('Email already registered. Please log in.', 'error')
        return redirect(url_for('account.signup'))

    # Profile photo upload (optional)
    profile_photo = 'default.jpg'
    if 'profile_photo' in request.files:
        saved = save_upload(request.files['profile_photo'])
        if saved:
            profile_photo = saved

    try:
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            phone=contact,   # contact form field maps to phone (canonical)
            address=address,
            profile_photo=profile_photo,
            role='customer',
        )
        new_user.generate_referral_code()

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        _seed_welcome_notifications(new_user.id)

        # Fire welcome email in background — never blocks the response
        try:
            from utils.mail import send_welcome_email
            import threading
            threading.Thread(
                target=send_welcome_email,
                args=(new_user,),
                daemon=True,
            ).start()
        except Exception as _me:
            current_app.logger.warning(f'Welcome email failed to start: {_me}')

        flash('Welcome to GrabBite! Your account has been created.', 'success')
        return redirect(url_for('public.index'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'signup_post error: {e}')
        flash('Error creating account. Please try again.', 'error')
        return redirect(url_for('account.signup'))


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE PROFILE
# ─────────────────────────────────────────────────────────────────────────────
def update_profile():
    if not current_user.is_authenticated:
        flash('Please log in to update your profile.', 'error')
        return redirect(url_for('account.login'))

    user             = current_user
    name             = request.form.get('name', '').strip()
    contact          = request.form.get('contact', '').strip()
    address_text     = request.form.get('address', '').strip()
    current_password = request.form.get('current_password', '')
    new_password     = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not name or len(name) < 2:
        flash('Name must be at least 2 characters.', 'error')
        return redirect(url_for('account.profile'))

    user.name    = name
    user.phone   = contact
    user.address = address_text

    # Password change
    if new_password:
        if not current_password:
            flash('Current password is required to set a new password.', 'error')
            return redirect(url_for('account.profile'))
        if not check_password_hash(user.password, current_password):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('account.profile'))
        if len(new_password) < 8:
            flash('New password must be at least 8 characters.', 'error')
            return redirect(url_for('account.profile'))
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('account.profile'))
        user.password = generate_password_hash(new_password)

    # Profile photo
    if 'profile_photo' in request.files:
        saved = save_upload(request.files['profile_photo'])
        if saved:
            # Delete old photo if not default
            if user.profile_photo and user.profile_photo != 'default.jpg':
                old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.profile_photo)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass
            user.profile_photo = saved

    try:
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'update_profile error: {e}')
        flash('Error updating profile. Please try again.', 'error')

    return redirect(url_for('account.profile'))


# ─────────────────────────────────────────────────────────────────────────────
# RESTAURANT OWNER REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────
def signup_owner_post():
    """Register a new restaurant owner + create their restaurant in one step."""
    from models import Restaurant

    # Owner account fields
    name             = request.form.get('name', '').strip()
    email            = request.form.get('email', '').strip().lower()
    contact          = request.form.get('contact', '').strip()
    password         = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Restaurant fields
    rest_name     = request.form.get('restaurant_name', '').strip()
    rest_location = request.form.get('restaurant_location', '').strip()
    rest_cuisine  = request.form.get('cuisine_type', '').strip()
    rest_phone    = request.form.get('restaurant_phone', '').strip()
    rest_desc     = request.form.get('restaurant_description', '').strip()

    # --- Validation ---
    if not all([name, email, password, confirm_password, rest_name, rest_location, rest_cuisine]):
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('account.signup_owner'))

    if not _EMAIL_RE.match(email):
        flash('Please enter a valid email address.', 'error')
        return redirect(url_for('account.signup_owner'))

    if len(password) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('account.signup_owner'))

    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('account.signup_owner'))

    if User.query.filter_by(email=email).first():
        flash('Email already registered. Please log in.', 'error')
        return redirect(url_for('account.signup_owner'))

    # Profile photo (optional)
    profile_photo = 'default.jpg'
    if 'profile_photo' in request.files:
        saved = save_upload(request.files['profile_photo'])
        if saved:
            profile_photo = saved

    # Restaurant banner image (optional)
    rest_image = 'restaurant_default.jpg'
    if 'restaurant_image' in request.files:
        saved = save_upload(request.files['restaurant_image'])
        if saved:
            rest_image = saved

    try:
        # 1. Create owner user
        owner = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            phone=contact,
            profile_photo=profile_photo,
            role='restaurant_owner',
            is_active=True,
        )
        owner.generate_referral_code()
        db.session.add(owner)
        db.session.flush()   # get owner.id before commit

        # 2. Create their restaurant
        restaurant = Restaurant(
            owner_id=owner.id,
            name=rest_name,
            location=rest_location,
            cuisine_type=rest_cuisine,
            description=rest_desc,
            phone=rest_phone or contact,
            image=rest_image,
            is_active=True,
            is_approved=False,   # admin must approve
        )
        db.session.add(restaurant)
        db.session.commit()

        # 3. Seed welcome notification
        _seed_welcome_notifications(owner.id)

        login_user(owner)
        flash(
            f'Welcome, {name}! Your restaurant "{rest_name}" has been registered '
            'and is pending admin approval. You can set up your menu now.',
            'success'
        )
        return redirect(url_for('owner.dashboard'))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'signup_owner_post error: {e}')
        flash('Error creating account. Please try again.', 'error')
        return redirect(url_for('account.signup_owner'))
