"""
Grabbite — API: Misc
/api/newsletter/subscribe, /api/footer/enquiry
"""
import os as _os
import json as _json

from flask import request, jsonify, current_app
from flask_login import current_user

from db import db
from models import Notification
from blueprints.api import api_bp


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
