"""
Grabbite — Admin: Payments
/admin/payments
"""
from flask import render_template
from flask_login import login_required

from models import Payment
from blueprints.admin import admin
from utils.decorators import admin_required


@admin.route('/payments')
@login_required
@admin_required
def payments():
    payment_list = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('admin/payments.html', payments=payment_list)
