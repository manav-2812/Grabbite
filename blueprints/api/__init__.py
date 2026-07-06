"""
Grabbite — API Package
Plan 3 refactor: splits blueprints/api_bp.py into domain sub-modules.

The single Blueprint object is created here and imported by every sub-module
so all @api_bp.route decorators register on the same blueprint.
app.py and blueprints/__init__.py import `api_bp` from here unchanged.
"""
from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import sub-modules so their @api_bp.route decorators fire.
# Order doesn't matter for route registration.
from blueprints.api import cart          # noqa: F401, E402
from blueprints.api import wishlist      # noqa: F401, E402
from blueprints.api import coupon        # noqa: F401, E402
from blueprints.api import address       # noqa: F401, E402
from blueprints.api import search        # noqa: F401, E402
from blueprints.api import reviews       # noqa: F401, E402
from blueprints.api import notifications # noqa: F401, E402
from blueprints.api import misc          # noqa: F401, E402

__all__ = ['api_bp']
