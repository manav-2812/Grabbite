"""
Grabbite — Admin: Support
/admin/support
"""
from flask import render_template
from flask_login import login_required

from models import SupportTicket
from blueprints.admin import admin
from utils.decorators import admin_required


@admin.route('/support')
@login_required
@admin_required
def support():
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return render_template('admin/support.html', tickets=tickets)
