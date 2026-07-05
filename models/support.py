"""
Grabbite — SupportTicket model.
"""
from db import db
from datetime import datetime, timezone


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKET
# ─────────────────────────────────────────────────────────────────────────────
class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject    = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    status     = db.Column(db.String(20), default='open')
    priority   = db.Column(db.String(20), default='medium')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SupportTicket "{self.subject[:40]}" {self.status}>'
