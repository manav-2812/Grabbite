import eventlet
eventlet.monkey_patch()

import os
from app import app

# Run DB migrations in a background thread so a slow DB connection
# cannot block server startup and fail the healthcheck.
import threading as _threading

def _run_migrations():
    try:
        from flask_migrate import upgrade as _db_upgrade
        with app.app_context():
            _db_upgrade()
        print('✅ DB migrations applied (or already up to date)')
    except Exception as _mig_err:
        print(f'⚠️  DB migration check failed: {_mig_err}')

_threading.Thread(target=_run_migrations, daemon=True).start()


try:
    from waitress import serve
except ImportError:
    serve = None

# Railway / Render inject PORT at runtime. Guard against the literal '$PORT'
# string that appears when CMD exec-form bypasses shell variable expansion.
HOST  = os.getenv('HOST', '0.0.0.0')
_port_raw = os.getenv('PORT', '8000').strip().lstrip('$')
try:
    PORT = int(_port_raw)
except ValueError:
    print(f"⚠️  Invalid PORT value '{_port_raw}', defaulting to 8000")
    PORT = 8000
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
