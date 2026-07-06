"""
Fix PostgreSQL sequences after a SQLite → Postgres migration.

When data is bulk-copied via INSERT (bypassing the sequence), all id_seq
sequences stay at their initial value (1). The next INSERT hits a duplicate
PK error because the sequence hands out an already-used id.

This script sets every sequence to MAX(id) so new inserts work.

Run once after copy_sqlite_to_pg.py:
    PYTHONPATH=. python scripts/fix_sequences.py
"""
from app import app, db

TABLES = [
    'users', 'restaurants', 'food_items', 'orders', 'payments', 'cart',
    'order_items', 'notifications', 'admin_notifications', 'admin_activities',
    'addresses', 'wishlist', 'order_status_history', 'reviews', 'blogs',
    'offers', 'coupon_usage', 'support_tickets', 'wallet_transactions',
]

with app.app_context():
    print('Fixing PostgreSQL sequences ...\n')
    for t in TABLES:
        seq_name = f'{t}_id_seq'
        try:
            max_id = db.session.execute(
                db.text(f'SELECT COALESCE(MAX(id), 0) FROM "{t}"')
            ).scalar()
            db.session.execute(
                db.text(f"SELECT setval('{seq_name}', :v, true)"),
                {'v': max(max_id, 1)}
            )
            new_val = db.session.execute(
                db.text(f"SELECT last_value FROM {seq_name}")
            ).scalar()
            status = 'OK' if new_val >= max_id else 'WARN'
            print(f'  {t:30s} max_id={max_id:5d}  seq_now={new_val:5d}  {status}')
        except Exception as e:
            print(f'  {t:30s} ERROR: {e}')
    db.session.commit()
    print('\nAll sequences fixed. New inserts will work correctly.')
