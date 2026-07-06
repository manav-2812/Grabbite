"""
Grabbite — Admin: Database Viewer
/admin/database
"""
import json

from flask import render_template, request, current_app
from flask_login import login_required

from db import db
from models import User, Restaurant, FoodItem, Order, Cart, Blog, Review, Offer, Payment, Notification
from blueprints.admin import admin
from utils.decorators import admin_required


@admin.route('/database')
@login_required
@admin_required
def database_viewer():
    """Admin database viewer — supports table selection and pagination."""
    import sqlalchemy as sa

    PER_PAGE = 50

    MODEL_MAP = {
        'users':         User,
        'restaurants':   Restaurant,
        'food_items':    FoodItem,
        'orders':        Order,
        'cart':          Cart,
        'blogs':         Blog,
        'reviews':       Review,
        'offers':        Offer,
        'payments':      Payment,
        'notifications': Notification,
    }

    table_names = list(MODEL_MAP.keys())

    table_counts = {}
    for key, model in MODEL_MAP.items():
        try:
            table_counts[key] = db.session.query(db.func.count(model.id)).scalar() or 0
        except Exception:
            table_counts[key] = 0
    table_counts_list = list(table_counts.items())

    current_table = request.args.get('table', table_names[0])
    if current_table not in MODEL_MAP:
        current_table = table_names[0]

    model = MODEL_MAP[current_table]
    page  = request.args.get('page', 1, type=int)

    table_schema = []
    col_names    = []
    try:
        sa_table = model.__table__
        pk_names = {c.name for c in sa_table.primary_key}
        fk_names = {list(c.foreign_keys)[0].parent.name
                    for c in sa_table.columns if c.foreign_keys}
        for col in sa_table.columns:
            table_schema.append({
                'name':        col.name,
                'type':        str(col.type),
                'nullable':    col.nullable,
                'primary_key': col.name in pk_names,
                'foreign_key': col.name in fk_names,
            })
        col_names = [c['name'] for c in table_schema]
    except Exception as exc:
        current_app.logger.error(f'database_viewer schema error: {exc}')

    try:
        pagination = model.query.order_by(model.id.desc()).paginate(
            page=page, per_page=PER_PAGE, error_out=False
        )
        items = []
        for row in pagination.items:
            row_dict = {}
            for col_name in col_names:
                val = getattr(row, col_name, None)
                if val is None:
                    row_dict[col_name] = 'NULL'
                elif isinstance(val, (list, dict)):
                    row_dict[col_name] = json.dumps(val, ensure_ascii=False)
                elif hasattr(val, 'isoformat'):
                    row_dict[col_name] = val.isoformat()
                else:
                    row_dict[col_name] = val
            items.append(row_dict)

        table_data = {
            'items':        items,
            'total':        pagination.total,
            'pages':        pagination.pages,
            'current_page': page,
            'has_prev':     pagination.has_prev,
            'has_next':     pagination.has_next,
        }
    except Exception as exc:
        table_data = {
            'items': [], 'total': 0, 'pages': 1, 'current_page': 1,
            'has_prev': False, 'has_next': False, 'error': str(exc),
        }

    return render_template(
        'database_viewer.html',
        current_table=current_table,
        table_names=table_names,
        table_counts=table_counts,
        table_counts_list=table_counts_list,
        table_schema=table_schema,
        table_data=table_data,
    )
