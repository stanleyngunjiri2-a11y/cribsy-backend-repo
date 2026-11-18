"""Small helpers shared by the route files."""
import re
from datetime import date
from functools import wraps

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from .extensions import db
from .models import ACTIVE_TENANCY, User

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def error(message, status=400, **extra):
    """Every error response has the same shape: {"error": "...", ...}."""
    return jsonify({"error": message, **extra}), status


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def is_email(value):
    return isinstance(value, str) and bool(EMAIL_RE.match(value.strip()))


def password_problem(password):
    """Same rules as the frontend. Returns a message, or '' if the password is fine."""
    if not isinstance(password, str) or len(password) < 8:
        return "Use at least 8 characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        return "Use both letters and numbers."
    return ""


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def roles_required(*roles):
    """Protect a route: the caller must be signed in, active, and have one of the roles."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = current_user()
            if user is None or user.status != "active":
                return error("This account is not active.", 403)
            if user.role not in roles:
                return error("You do not have permission to do this.", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def active_tenancy_for(user):
    """The tenancy a tenant is currently living in, or None."""
    from .models import Tenancy

    return (
        Tenancy.query.filter(Tenancy.tenant_id == user.id, Tenancy.status.in_(ACTIVE_TENANCY))
        .order_by(Tenancy.id.desc())
        .first()
    )


def send_email(to, subject, body):
    """Deliver a plain-text email through SendGrid.

    Returns True when SendGrid accepts the message and False when delivery
    cannot be submitted. Never logs API keys or message contents.
    """
    api_key = current_app.config.get("SENDGRID_API_KEY")
    from_email = current_app.config.get("SENDGRID_FROM_EMAIL")

    if not api_key or not from_email:
        current_app.logger.error(
            "Email delivery is not configured: missing SendGrid API key or sender."
        )
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=from_email,
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )

        response = SendGridAPIClient(api_key).send(message)

        if 200 <= response.status_code < 300:
            current_app.logger.info(
                "SendGrid accepted email to %s (HTTP %s).",
                to,
                response.status_code,
            )
            return True

        current_app.logger.error(
            "SendGrid rejected email to %s (HTTP %s).",
            to,
            response.status_code,
        )
        return False

    except Exception:
        current_app.logger.exception("SendGrid email submission failed for %s.", to)
        return False


def notify(user, subject, body):
    """Send an email notification only if the user has not turned notifications off."""
    if user.email_notifications:
        return send_email(user.email, subject, body)
    return False
