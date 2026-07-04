"""
Grabbite — Shared Extension Instances
HIGH-4/5: Created as part of the blueprint refactor so that db, socketio,
login_manager, and limiter can be imported by blueprints without circular imports.

Usage in blueprints:
    from extensions import db, socketio, login_manager, limiter
"""
# Re-export db from its existing module so all existing `from db import db`
# imports continue to work without changes.
from db import db  # noqa: F401

# These are populated by app.py after the app is created.
# Blueprints import them after init, so no circular import.
socketio = None    # replaced in app.py: extensions.socketio = socketio
login_manager = None
limiter = None
