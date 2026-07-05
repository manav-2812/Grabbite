"""
Grabbite — Notification & AdminNotification models.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATION
# ─────────────────────────────────────────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title      = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    type       = db.Column(db.String(50))
    link       = db.Column(db.String(255))
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(
        self,
        user_id: int = 0,
        title: str = '',
        message: str = '',
        type: Optional[str] = None,
        link: Optional[str] = None,
        is_read: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.user_id = user_id
        self.title = title
        self.message = message
        self.type = type
        self.link = link
        self.is_read = is_read

    def __repr__(self):
        return f'<Notification user={self.user_id} "{self.title[:30]}">'


class AdminNotification(db.Model):
    __tablename__ = 'admin_notifications'

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(200), nullable=False)
    message      = db.Column(db.Text, nullable=False)
    type         = db.Column(db.String(50), default='general')
    target_users = db.Column(db.String(50), default='all')
    is_sent      = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at      = db.Column(db.DateTime)

    def __init__(
        self,
        title: str = '',
        message: str = '',
        type: str = 'general',
        target_users: str = 'all',
        is_sent: bool = False,
        sent_at: Optional[datetime] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.title = title
        self.message = message
        self.type = type
        self.target_users = target_users
        self.is_sent = is_sent
        self.sent_at = sent_at

    def __repr__(self):
        return f'<AdminNotification "{self.title[:30]}">'
