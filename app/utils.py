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
    """Development version: writes the email to the server log.
    Replace the body of this function with Flask-Mail or a provider's API later."""
    current_app.logger.info("EMAIL to=%s | subject=%s\n%s", to, subject, body)


def notify(user, subject, body):
    """Send an email notification only if the user has not turned notifications off."""
    if user.email_notifications:
        send_email(user.email, subject, body)
