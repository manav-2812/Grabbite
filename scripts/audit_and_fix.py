"""
Grabbite — Full DB audit + sequence fix + integrity check.
Run: PYTHONPATH=d:/Grabbite/Grabbite python scripts/audit_and_fix.py
"""
import sys
sys.path.insert(0, 'd:/Grabbite/Grabbite')

from app import app, db

TABLES = [
    'users', 'restaurants', 'food_items', 'orders', 'payments', 'cart',
    'order_items', 'notifications', 'admin_notifications', 'admin_activities',
    'addresses', 'wishlist', 'order_status_history', 'reviews', 'blogs',
    'offers', 'coupon_usage', 'support_tickets', 'wallet_transactions',
]

with app.app_context():
    # ── 1. Check all expected tables exist ──────────────────────────────────
    print('=' * 60)
    print('1. TABLE PRESENCE CHECK')
    print('=' * 60)
    existing = {r[0] for r in db.session.execute(db.text(
        "SELECT tablename FROM pg_tables WHERE schemaname='public'"
    )).fetchall()}
    all_present = True
    for t in TABLES:
        status = '✅' if t in existing else '❌ MISSING'
        if t not in existing:
            all_present = False
        count = db.session.execute(db.text(f'SELECT COUNT(*) FROM "{t}"')).scalar() if t in existing else 0
        print(f'  {t:30s} {status}  rows={count}')
    print(f'\n  Result: {"All tables present ✅" if all_present else "Some tables missing ❌"}')

    # ── 2. Sequence check & fix ──────────────────────────────────────────────
    print('\n' + '=' * 60)
    print('2. SEQUENCE CHECK & FIX')
    print('=' * 60)
    fixed = 0
    for t in TABLES:
        if t not in existing:
            continue
        seq_name = f'{t}_id_seq'
        try:
            max_id = db.session.execute(
                db.text(f'SELECT COALESCE(MAX(id), 0) FROM "{t}"')
            ).scalar()
            current_seq = db.session.execute(
                db.text(f"SELECT last_value FROM {seq_name}")
            ).scalar()
            if current_seq < max_id:
                db.session.execute(
                    db.text(f"SELECT setval('{seq_name}', :v, true)"),
                    {'v': max_id}
                )
                new_val = db.session.execute(
                    db.text(f"SELECT last_value FROM {seq_name}")
                ).scalar()
                print(f'  FIXED  {t:30s} seq: {current_seq} -> {new_val}')
                fixed += 1
            else:
                print(f'  OK     {t:30s} seq={current_seq}  max_id={max_id}')
        except Exception as e:
            print(f'  SKIP   {t:30s} ({e})')
    db.session.commit()
    print(f'\n  Fixed {fixed} sequences.')

    # ── 3. FK integrity check (nulls & orphans that would break inserts) ─────
    print('\n' + '=' * 60)
    print('3. FOREIGN KEY INTEGRITY CHECK')
    print('=' * 60)
    # Only check non-nullable FKs — nullable ones (owner_id, etc.) are fine as NULL
    fk_checks = [
        # (child_table, child_col, parent_table, parent_col, nullable)
        ('order_status_history', 'order_id',     'orders',      'id',  False),
        ('order_items',          'order_id',     'orders',      'id',  False),
        ('payments',             'order_id',     'orders',      'id',  False),
        ('notifications',        'user_id',      'users',       'id',  False),
        ('cart',                 'user_id',      'users',       'id',  False),
        ('cart',                 'food_item_id', 'food_items',  'id',  False),
        ('orders',               'user_id',      'users',       'id',  False),
        ('orders',               'restaurant_id','restaurants', 'id',  False),
        ('food_items',           'restaurant_id','restaurants', 'id',  False),
        ('reviews',              'user_id',      'users',       'id',  False),
        # nullable FKs — only check orphans, not NULLs
        ('restaurants',          'owner_id',     'users',       'id',  True),
        ('payments',             'user_id',      'users',       'id',  True),
    ]
    bad_rows = []
    for child, col, parent, pcol, nullable in fk_checks:
        if child not in existing or parent not in existing:
            continue
        if not nullable:
            nulls = db.session.execute(db.text(
                f'SELECT COUNT(*) FROM "{child}" WHERE "{col}" IS NULL'
            )).scalar()
        else:
            nulls = 0
        orphans = db.session.execute(db.text(
            f'SELECT COUNT(*) FROM "{child}" c '
            f'LEFT JOIN "{parent}" p ON c."{col}"=p."{pcol}" '
            f'WHERE c."{col}" IS NOT NULL AND p."{pcol}" IS NULL'
        )).scalar()
        if nulls or orphans:
            print(f'  ❌ {child}.{col}: {nulls} NULLs, {orphans} orphans')
            if not nullable and nulls:
                bad_rows.append((child, col, nulls))
        else:
            print(f'  ✅ {child}.{col}  (nullable={nullable})')

    # Only delete rows with NULL on non-nullable FKs — these break inserts
    if bad_rows:
        print('\n  Removing NULL FK rows on non-nullable columns...')
        for child, col, count in bad_rows:
            try:
                r = db.session.execute(db.text(
                    f'DELETE FROM "{child}" WHERE "{col}" IS NULL'
                ))
                print(f'  Deleted {r.rowcount} rows from {child} where {col} IS NULL')
            except Exception as e:
                db.session.rollback()
                print(f'  Could not clean {child}.{col}: {e}')
        db.session.commit()

    # ── 4. Test a live INSERT cycle (order placement smoke test) ────────────
    print('\n' + '=' * 60)
    print('4. ORDER PLACEMENT SMOKE TEST')
    print('=' * 60)
    from models import (User, Restaurant, FoodItem, Order, OrderItem,
                        Payment, OrderStatusHistory, Notification)
    user       = User.query.filter_by(role='customer').first() or User.query.first()
    restaurant = Restaurant.query.filter_by(is_active=True).first()
    food       = FoodItem.query.filter_by(
        restaurant_id=restaurant.id, is_available=True
    ).first() if restaurant else None

    if not user or not restaurant or not food:
        print('  SKIP — no user/restaurant/food found to test with')
    else:
        print(f'  User: #{user.id} {user.email}')
        print(f'  Restaurant: #{restaurant.id} {restaurant.name}')
        print(f'  FoodItem: #{food.id} {food.name} ₹{food.price}')
        try:
            order = Order(
                user_id=user.id,
                restaurant_id=restaurant.id,
                order_items=[{
                    'id': food.id, 'name': food.name, 'quantity': 1,
                    'price': float(food.price), 'total': float(food.price)
                }],
                subtotal=float(food.price),
                tax=round(float(food.price) * 0.18, 2),
                delivery_fee=40.0,
                discount=0.0,
                total_amount=round(float(food.price) * 1.18 + 40.0 + 5.0, 2),
                delivery_address='123 Test Street, Test City',
                delivery_phone='9876543210',
                payment_method='cod',
                payment_status='pending',
                status='placed',
            )
            db.session.add(order)
            db.session.flush()
            print(f'  Order ID assigned: {order.id}')

            db.session.add(OrderItem(
                order_id=order.id, food_item_id=food.id,
                name=food.name, price=float(food.price), quantity=1
            ))
            db.session.add(Payment(
                order_id=order.id, user_id=user.id,
                amount=order.total_amount, payment_method='cod', status='pending'
            ))
            db.session.add(OrderStatusHistory(
                order_id=order.id, status='placed', note='Smoke test'
            ))
            db.session.add(Notification(
                user_id=user.id, title='Test Order',
                message='Smoke test notification',
                type='order_update', link='/orders'
            ))
            db.session.commit()
            print(f'  ✅ Order #{order.id} committed successfully!')

            # Clean up the test row
            db.session.delete(order)
            db.session.commit()
            print('  ✅ Cleanup done. ORDER PLACEMENT IS WORKING.')
        except Exception as e:
            db.session.rollback()
            print(f'  ❌ Order placement FAILED: {e}')
            import traceback
            traceback.print_exc()

    print('\n' + '=' * 60)
    print('AUDIT COMPLETE')
    print('=' * 60)
