"""
Grabbite — config.py

MED-1: This file is DEPRECATED.

All application configuration is now managed directly in app.py via
``app.config.update(...)`` which reads from environment variables.
This file is kept to avoid ImportError in any legacy import paths that
reference it (e.g. older migration scripts).

DO NOT add new configuration here. Edit app.py instead.

If you need environment-specific config classes in the future,
consider using Flask's built-in class-based config approach and
reference it from app.py's create_app() factory.
"""

# Stub: export an empty config dict so any ``from config import config``
# import still works without a NameError.
config = {}
