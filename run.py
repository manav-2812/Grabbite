import os
from app import app

try:
    from waitress import serve
except ImportError:
    serve = None

# Configuration
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
# MED-12 fix: debug mode must default to OFF.
# Leaving DEBUG=True as the default means a developer who forgets to
# export FLASK_DEBUG=False in prod boots a publicly-reachable debugger.
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
