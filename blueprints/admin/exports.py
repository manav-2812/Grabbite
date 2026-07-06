"""
Grabbite — Admin: CSV Exports
/admin/export/orders, /admin/export/users, /admin/export/payments

M18 fix: prevent CSV formula injection (CWE-1236). Cells whose first
character is one of = + - @ (tab) (CR) get prefixed with a single quote so
Excel / LibreOffice don't interpret them as formulas.
"""
import csv
import io

from flask import Response
from flask_login import login_required

from models import Order, User, Payment
from blueprints.admin import admin
from utils.decorators import admin_required

CSV_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def csv_safe(value) -> str:
    s = '' if value is None else str(value)
    if s and s[0] in CSV_FORMULA_PREFIXES:
        s = "'" + s
    return s


@admin.route('/export/orders')
@login_required
@admin_required
def export_orders():
    """Download all orders as CSV."""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User', 'Restaurant', 'Amount', 'Status',
                     'Payment Method', 'Payment Status', 'Date'])
    for o in orders:
        writer.writerow([
            o.id,
            csv_safe(o.user.name if o.user else ''),
            csv_safe(o.restaurant.name if o.restaurant else ''),
            o.total_amount,
            csv_safe(o.status),
            csv_safe(o.payment_method),
            csv_safe(o.payment_status),
            csv_safe(o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else ''),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=orders.csv'},
    )


@admin.route('/export/users')
@login_required
@admin_required
def export_users():
    """Download all users as CSV."""
    users = User.query.order_by(User.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Name', 'Email', 'Phone', 'Role',
                     'Active', 'Joined', 'Last Login'])
    for u in users:
        writer.writerow([
            u.id, csv_safe(u.name), csv_safe(u.email), csv_safe(u.phone or u.contact),
            csv_safe(u.role), u.is_active,
            csv_safe(u.created_at.strftime('%Y-%m-%d') if u.created_at else ''),
            csv_safe(u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else ''),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=users.csv'},
    )


@admin.route('/export/payments')
@login_required
@admin_required
def export_payments():
    """Download all payments as CSV."""
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Order ID', 'Amount', 'Method', 'Status',
                     'Gateway', 'Gateway Payment ID', 'Date'])
    for p in payments:
        writer.writerow([
            p.id, p.order_id, p.amount, csv_safe(p.payment_method),
            csv_safe(p.status), csv_safe(p.gateway),
            csv_safe(p.gateway_payment_id or ''),
            csv_safe(p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else ''),
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=payments.csv'},
    )
