"""
Grabbite — Admin Package
Plan 1 refactor: splits admin_routes.py into domain sub-modules.

The single Blueprint object ('admin') is created here. All sub-modules
import `admin` from this package so their @admin.route decorators register
on the same blueprint. app.py switches from:
    from admin_routes import admin as admin_blueprint
to:
    from blueprints.admin import admin as admin_blueprint
"""
from flask import Blueprint, current_app, request
from flask_login import current_user
from datetime import datetime, timezone

from db import db
from models import AdminActivity
from utils.decorators import admin_required, owner_required  # noqa: F401
from utils.uploads import (                                  # noqa: F401
    allowed_file, _looks_like_image, save_image, save_upload
)

admin = Blueprint('admin', __name__)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def broadcast_update(event_type, data, room='authenticated_users'):
    """Broadcast real-time updates — wrapped so failure doesn't crash the app."""
    try:
        from app import socketio
        socketio.emit('real_time_update', {
            'type':      event_type,
            'data':      data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, room=room)  # type: ignore[call-arg]
    except Exception as exc:
        current_app.logger.debug(f'broadcast_update({event_type}) skipped: {exc}')


def log_admin_activity(action, target_type, target_id=None, details=None):
    """Log admin activity to the activity table."""
    try:
        activity = AdminActivity(
            admin_id=current_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=request.remote_addr,
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        current_app.logger.warning(f'log_admin_activity failed: {e}')



# Import sub-modules so their @admin.route decorators fire.
from blueprints.admin import dashboard      # noqa: F401, E402
from blueprints.admin import database       # noqa: F401, E402
from blueprints.admin import restaurants    # noqa: F401, E402
from blueprints.admin import dishes         # noqa: F401, E402
from blueprints.admin import users          # noqa: F401, E402
from blueprints.admin import orders         # noqa: F401, E402
from blueprints.admin import blogs          # noqa: F401, E402
from blueprints.admin import offers         # noqa: F401, E402
from blueprints.admin import reviews        # noqa: F401, E402
from blueprints.admin import payments       # noqa: F401, E402
from blueprints.admin import notifications  # noqa: F401, E402
from blueprints.admin import support        # noqa: F401, E402
from blueprints.admin import exports        # noqa: F401, E402

__all__ = ['admin']
