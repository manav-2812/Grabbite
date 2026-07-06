"""
Grabbite — Socket Events
WebSocket event handlers and the broadcast_update helper.
Extracted from app.py (Plan 2 refactor).

Usage in app.py:
    from utils.socket_events import register_socket_events
    register_socket_events(socketio)
"""
from datetime import datetime, timezone
from flask_login import current_user
from flask_socketio import join_room, leave_room, emit


def register_socket_events(socketio):
    """Register all @socketio.on(...) handlers onto the given SocketIO instance."""

    @socketio.on('connect')
    def handle_connect():
        if current_user.is_authenticated:
            join_room('authenticated_users')
            if current_user.is_administrator():
                join_room('admin_users')

    @socketio.on('disconnect')
    def handle_disconnect():
        if current_user.is_authenticated:
            leave_room('authenticated_users')
            if current_user.is_administrator():
                leave_room('admin_users')

    @socketio.on('join_admin')
    def handle_join_admin():
        if current_user.is_authenticated and current_user.is_administrator():
            join_room('admin_users')
            emit('status', {'msg': 'Joined admin room'})


def broadcast_update(socketio, event_type, data, room='authenticated_users'):
    """Broadcast real-time updates to connected clients.

    Args:
        socketio: The Flask-SocketIO instance.
        event_type: String label for the event (e.g. 'order_update').
        data: JSON-serializable payload dict.
        room: SocketIO room to broadcast to (default: all authenticated users).
    """
    try:
        socketio.emit('real_time_update', {
            'type':      event_type,
            'data':      data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }, room=room)  # type: ignore[call-arg]
    except Exception:
        pass  # Don't crash the app if no socket connections
