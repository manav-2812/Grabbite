import os
from app import app

# Run DB migrations automatically on every startup.
# Flask-Migrate / Alembic is idempotent — if already at head, this is a no-op.
# This avoids a manual `flask db upgrade` step after every deploy.
try:
    from flask_migrate import upgrade as _db_upgrade
    with app.app_context():
        _db_upgrade()
    print('✅ DB migrations applied (or already up to date)')
except Exception as _mig_err:
    print(f'⚠️  DB migration check failed: {_mig_err}')
    # Don't crash the server — schema may still be usable.

try:
    from waitress import serve
except ImportError:
    serve = None

# Railway injects PORT automatically; default to 8000 for Docker, 5000 for local dev
HOST  = os.getenv('HOST',  '0.0.0.0')
PORT  = int(os.getenv('PORT', 8000))
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

def run_development_server():
    """Run the application in development mode"""
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG
    )

def run_production_server():
    """Run the application in production mode using waitress"""
    if serve is None:
        print("waitress is not installed; falling back to Flask development server")
        run_development_server()
        return
    print(f"Starting production server on {HOST}:{PORT}")
    serve(
        app,
        host=HOST,
        port=PORT,
        threads=4
    )

if __name__ == "__main__":
    try:
        if DEBUG:
            print("Running in development mode")
            run_development_server()
        else:
            print("Running in production mode")
            run_production_server()
    except Exception as e:
        print(f"Error starting server: {e}")
        raise
