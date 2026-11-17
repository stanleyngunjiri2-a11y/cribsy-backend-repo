# server/utils.py

from functools import wraps  # <-- ADD THIS LINE
from flask import jsonify, request, current_app
from flask_jwt_extended import get_jwt_identity
from .extension import db
from ..models import User

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def error(message, status_code=400):
    return jsonify({"error": message}), status_code


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
    # This is a placeholder for whatever notification logic you have
    print(f"Notification for {user.email}: {title} - {message}")


# SENDGRID EMAIL FUNCTION


def send_email(to_email, subject, html_content):
    # Make sure this matches the verified sender in your SendGrid dashboard
    from_email = "your_verified_sender@example.com"

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=html_content,
    )

    try:
        # Pull the key securely from your config.py
        api_key = current_app.config.get("SENDGRID_API_KEY")

        if not api_key:
            print("WARNING: SENDGRID_API_KEY is not set in config.")
            return False

        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"✅ Email sent to {to_email}! Status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False
