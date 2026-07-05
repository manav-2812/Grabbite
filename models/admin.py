"""
Grabbite — AdminActivity model.
"""
from db import db
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN ACTIVITY LOG
# ─────────────────────────────────────────────────────────────────────────────
class AdminActivity(db.Model):
    __tablename__ = 'admin_activities'

    id          = db.Column(db.Integer, primary_key=True)
    admin_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action      = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id   = db.Column(db.Integer)
    details     = db.Column(db.Text)
    ip_address  = db.Column(db.String(45))
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    admin = db.relationship('User', backref='admin_activities', lazy=True)

    def __init__(
        self,
        admin_id: int = 0,
        action: str = '',
        target_type: str = '',
        target_id: Optional[int] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self.admin_id = admin_id
        self.action = action
        self.target_type = target_type
        self.target_id = target_id
        self.details = details
        self.ip_address = ip_address

    def __repr__(self):
        return f'<AdminActivity {self.action} by admin={self.admin_id}>'
