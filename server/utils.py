# server/utils.py

from functools import wraps  # <-- ADD THIS LINE
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity
from .extension import db
from .models import User
from email_service import send_email




def error(message, status_code=400, fields=None):
    response = {"error": message}

    if fields:
        response["fields"] = fields

    return jsonify(response), status_code

def json_body():
    return request.get_json() or {}


def current_user():
    user_id = get_jwt_identity()
    return db.session.get(User, user_id)


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)  # This will now work because of the import above!
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user or user.role not in roles:
                return error("Unauthorized", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator



def notify(user, title, message):
    if not user:
        print("Notification skipped: user not found.")
        return

    print(f"Notification for {user.email}: {title} - {message}")

    if not user.email:
        print("Email not sent: user has no email address.")
        return

    html_content = f"""
        <h2>{title}</h2>
        <p>{message}</p>
        <p>Thank you for using Cribsy!</p>
    """

    result = send_email(
        to_email=user.email,
        subject=title,
        html_content=html_content
    )

    if result:
        print(f"Email notification accepted for {user.email}")
    else:
        print(f"Email notification failed for {user.email}")



