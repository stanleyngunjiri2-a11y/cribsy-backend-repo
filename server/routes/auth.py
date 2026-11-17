from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from ..extension import db
from ..models import User
from ..utils import error, json_body, send_email

bp = Blueprint("auth", __name__)
URL_PREFIX = "/api/auth"

# A temporary dictionary to store codes in memory for testing

DEV_CODES = {}


@bp.post("/login")
def login():
    data = json_body()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or user.password != password:
        return error("Invalid email or password", 401)

    code = "123456"
    DEV_CODES[email] = code

    email_sent = send_email(
        to_email=user.email,
        subject="Your Cribsy Verification Code",
        html_content=f"<strong>Welcome back!</strong><br>Your code is: {code}",
    )

    response_data = {"message": "Login successful. Verification code sent."}

    from flask import current_app

    if current_app.config.get("SHOW_DEV_CODES"):
        response_data["dev_code"] = code

    return jsonify(response_data), 200


@bp.post("/verify")
def verify():
    data = json_body()
    email = data.get("email")
    code = data.get("code")

    if not email or not code:
        return error("Email and code are required", 400)

    expected_code = DEV_CODES.get(email)

    if expected_code != code:
        return error("Invalid or expired code", 400)

    user = User.query.filter_by(email=email).first()
    if not user:
        return error("User not found", 404)

    del DEV_CODES[email]

    access_token = create_access_token(identity=str(user.id))

    return (
        jsonify({"message": "Verification successful", "access_token": access_token}),
        200,
    )
