"""
Grabbite — Email Utility Module
=================================
Initialises Flask-Mail and exposes one public helper:

    send_mail(to, subject, html)    — fire-and-forget, logs errors silently
    send_welcome_email(user)
    send_order_confirmation(user, order)
    send_order_status_update(user, order, new_status)
    send_password_reset_email(user, token)
    send_password_reset_success(user)
    send_restaurant_approved_email(user, restaurant)

Mail is disabled gracefully when MAIL_SERVER is not configured so the
app still boots in dev without any SMTP credentials.
"""
from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING

from flask import current_app, render_template
from flask_mail import Mail, Message

if TYPE_CHECKING:
    from models import User, Order, Restaurant

logger = logging.getLogger(__name__)

# Module-level Mail instance — initialised in init_mail()
mail = Mail()


def init_mail(app) -> None:
    """Call this once from the app factory (app.py) after app.config is set."""
    mail.init_app(app)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _is_configured() -> bool:
    """Return True only when a real SMTP server has been configured."""
    return bool(current_app.config.get('MAIL_SERVER'))


def _debug_print_email(to, subject: str, body: str) -> None:
    """Print a nicely-formatted email to the terminal for local dev."""
    sep = '=' * 64
    print(f'\n{sep}')
    print(f'  [GRABBITE EMAIL]')
    print(sep)
    print(f'  To      : {to}')
    print(f'  Subject : {subject}')
    print(f'  {"-" * 60}')
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            try:
                print(f'  {stripped}')
            except UnicodeEncodeError:
                # Encode to ASCII, replacing any unencodable chars
                print(f'  {stripped.encode("ascii", errors="replace").decode("ascii")}')
    print(f'{sep}\n')


def send_mail(to: str | list[str], subject: str, html: str, text: str = '') -> bool:
    """
    Send an HTML email. Returns True on success, False on any failure.
    In development (MAIL_SERVER not set) the email is printed to the terminal
    instead of being silently dropped, so you can see and test every email
    without needing real SMTP credentials.
    """
    recipients = [to] if isinstance(to, str) else to
    plain_body = text or _html_to_plain(html)

    if not _is_configured():
        # ── DEBUG MODE: print to terminal ─────────────────────────────────
        _debug_print_email(', '.join(recipients), subject, plain_body)
        logger.info('[DEBUG MAIL] Email printed to terminal for: %s — %s', recipients, subject)
        return True   # return True so callers see "email handled"

    sender = current_app.config.get('MAIL_DEFAULT_SENDER') or \
             current_app.config.get('MAIL_USERNAME', 'noreply@grabbite.com')

    try:
        msg = Message(
            subject=subject,
            sender=sender,
            recipients=recipients,
            html=html,
            body=plain_body,
        )
        mail.send(msg)
        logger.info('Email sent to %s — %s', recipients, subject)
        return True
    except Exception as exc:
        logger.error('Failed to send email to %s — %s: %s', recipients, subject, exc)
        return False


def _html_to_plain(html: str) -> str:
    """Very basic HTML → plain-text strip for the text/plain part."""
    import re
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── Public email builders ────────────────────────────────────────────────────

def send_welcome_email(user) -> bool:
    """Welcome email sent after a successful signup."""
    html = render_template('emails/welcome.html', user=user)
    return send_mail(
        to=user.email,
        subject='🎉 Welcome to GrabBite — Let\'s get your first order in!',
        html=html,
    )


def send_order_confirmation(user, order) -> bool:
    """Order confirmation sent immediately after the order is placed."""
    html = render_template('emails/order_confirmation.html', user=user, order=order)
    return send_mail(
        to=user.email,
        subject=f'✅ GrabBite Order #{order.id} Confirmed — Food is on its way!',
        html=html,
    )


def send_order_status_update(user, order, new_status: str) -> bool:
    """Notify the user every time their order status changes."""
    status_labels = {
        'accepted':   '👍 Order Accepted',
        'preparing':  '👨‍🍳 Being Prepared',
        'ready':      '📦 Ready for Pickup',
        'picked':     '🏍️ Picked Up',
        'on_the_way': '🚴 On the Way',
        'delivered':  '🎉 Delivered!',
        'cancelled':  '❌ Order Cancelled',
        'refunded':   '💰 Refund Initiated',
    }
    label = status_labels.get(new_status, new_status.replace('_', ' ').title())
    html = render_template(
        'emails/order_status.html',
        user=user, order=order, new_status=new_status, label=label,
    )
    return send_mail(
        to=user.email,
        subject=f'GrabBite Order #{order.id} — {label}',
        html=html,
    )


def send_password_reset_email(user, token: str) -> bool:
    """Password-reset link email. Token is a URL-safe signed string."""
    from flask import url_for
    reset_url = url_for('account.forgot_password_reset', token=token, _external=True)
    html = render_template(
        'emails/password_reset.html',
        user=user, reset_url=reset_url,
    )
    return send_mail(
        to=user.email,
        subject='🔑 GrabBite — Reset your password',
        html=html,
    )


def send_password_reset_success(user) -> bool:
    """Confirmation email after a password has been successfully reset."""
    html = render_template('emails/password_reset_success.html', user=user)
    return send_mail(
        to=user.email,
        subject='🔐 GrabBite — Your password has been changed',
        html=html,
    )


def send_restaurant_approved_email(user, restaurant) -> bool:
    """Notify a restaurant owner that their listing was approved by admin."""
    from flask import url_for
    dashboard_url = url_for('owner.dashboard', _external=True)
    html = render_template(
        'emails/restaurant_approved.html',
        user=user, restaurant=restaurant, dashboard_url=dashboard_url,
    )
    return send_mail(
        to=user.email,
        subject=f'🚀 GrabBite — "{restaurant.name}" is now live!',
        html=html,
    )
