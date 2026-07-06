"""
Grabbite — Admin: Offers Management
/admin/offers, /admin/offers/add, /admin/offers/toggle/<id>
"""
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required

from db import db
from models import Offer
from blueprints.admin import admin, log_admin_activity
from utils.decorators import admin_required


@admin.route('/offers')
@login_required
@admin_required
def offers():
    offer_list = Offer.query.order_by(Offer.created_at.desc()).all()
    return render_template('admin/offers.html', offers=offer_list)


@admin.route('/offers/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_offer():
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.form.get('start_date', ''), '%Y-%m-%dT%H:%M')
            end_date   = datetime.strptime(request.form.get('end_date', ''), '%Y-%m-%dT%H:%M')

            offer = Offer(
                title=request.form.get('title'),
                description=request.form.get('description'),
                discount_type=request.form.get('discount_type'),
                discount_value=float(request.form.get('discount_value', 0)),
                min_order_amount=float(request.form.get('min_order_amount', 0)),
                max_discount=request.form.get('max_discount', None, type=float),
                code=request.form.get('code', '').upper() or None,
                start_date=start_date,
                end_date=end_date,
                usage_limit=request.form.get('usage_limit', None, type=int),
                is_active=request.form.get('is_active') == 'on',
            )
            db.session.add(offer)
            db.session.commit()
            log_admin_activity('Added Offer', 'offer', offer.id)
            flash('Offer added successfully!', 'success')
            return redirect(url_for('admin.offers'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error adding offer: {str(e)}', 'error')

    return render_template('admin/offers.html', offers=Offer.query.all(), show_add_form=True)


@admin.route('/offers/toggle/<int:offer_id>', methods=['POST'])
@login_required
@admin_required
def toggle_offer(offer_id):
    try:
        offer = Offer.query.get_or_404(offer_id)
        offer.is_active = not offer.is_active
        db.session.commit()
        status = 'activated' if offer.is_active else 'deactivated'
        flash(f'Offer {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
    return redirect(url_for('admin.offers'))
