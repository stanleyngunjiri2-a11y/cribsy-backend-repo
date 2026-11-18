"""OWNER: Member 1 (Stanley). Registration, two-step sign-in, password reset and the signed-in user's profile."""
import secrets
from datetime import timedelta

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User, VerificationCode, utcnow
from ..utils import current_user, error, is_email, json_body, password_problem, send_email

bp = Blueprint("auth", __name__)
URL_PREFIX = "/api/auth"

CODE_MINUTES = 10


def reset_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


@bp.post("/register")
def register():
    data = json_body()
    full_name = str(data.get("full_name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    phone = str(data.get("phone") or "").strip()
    role = data.get("role")
    password = data.get("password")

    fields = {}
    if len(full_name) < 2:
        fields["full_name"] = "Enter your full name."
    if not is_email(email):
        fields["email"] = "Enter a valid email address."
    if len(phone) < 9:
        fields["phone"] = "Enter a valid phone number."
    if role not in ("tenant", "landlord"):  # admins are created by the team, never self-registered
        fields["role"] = "Choose tenant or landlord."
    problem = password_problem(password)
    if problem:
        fields["password"] = problem
    if fields:
        return error("Please fix the highlighted fields.", 400, fields=fields)

    if User.query.filter_by(email=email).first():
        return error("An account with this email already exists.", 409,
                     fields={"email": "This email is already registered."})

    user = User(full_name=full_name, email=email, phone=phone, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@bp.post("/login")
def login():
    """Step 1: check the password and email a 6-digit code."""
    data = json_body()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        return error("Incorrect email or password.", 401)
    if user.status != "active":
        return error("This account has been suspended.", 403)

    code = f"{secrets.randbelow(1_000_000):06d}"
    VerificationCode.query.filter_by(user_id=user.id, used=False).update({"used": True})
    db.session.add(VerificationCode(
        user_id=user.id,
        code_hash=generate_password_hash(code),
        expires_at=utcnow() + timedelta(minutes=CODE_MINUTES),
    ))
    db.session.commit()

    send_email(user.email, "Your RentConnect verification code",
               f"Your code is {code}. It expires in {CODE_MINUTES} minutes.")

    body = {"verification_required": True, "email": user.email, "message": "Verification code sent."}
    if current_app.config["SHOW_DEV_CODES"]:
        body["dev_code"] = code
    return jsonify(body)


@bp.post("/verify")
def verify():
    """Step 2: exchange the code for an access token."""
    data = json_body()
    email = str(data.get("email") or "").strip().lower()
    code = str(data.get("code") or "")

    user = User.query.filter_by(email=email).first()
    if user is None or user.status != "active":
        return error("The code is incorrect or has expired.", 400)

    record = (
        VerificationCode.query.filter_by(user_id=user.id, used=False)
        .order_by(VerificationCode.id.desc())
        .first()
    )
    if record is None or record.expires_at < utcnow() or not check_password_hash(record.code_hash, code):
        return error("The code is incorrect or has expired.", 400)

    record.used = True
    db.session.commit()

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"access_token": token, "user": user.to_dict()})


@bp.post("/forgot-password")
def forgot_password():
    email = str(json_body().get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()

    body = {"message": "If that email is registered, a reset link has been sent."}
    if user and user.status == "active":
        # The token also contains part of the current password hash, so it stops working once used.
        token = reset_serializer().dumps({"id": user.id, "p": user.password_hash[-12:]})
        link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={token}"
        send_email(user.email, "Reset your RentConnect password",
                   f"Use this link within 1 hour to set a new password:\n{link}")
        if current_app.config["SHOW_DEV_CODES"]:
            body["dev_reset_link"] = link
    return jsonify(body)  # same answer whether or not the email exists


@bp.post("/reset-password")
def reset_password():
    data = json_body()
    token = data.get("token")
    password = data.get("password")

    problem = password_problem(password)
    if problem:
        return error("Please fix the highlighted fields.", 400, fields={"password": problem})
    if not isinstance(token, str):
        return error("This reset link is invalid.", 400)

    try:
        payload = reset_serializer().loads(token, max_age=3600)
    except SignatureExpired:
        return error("This reset link has expired.", 400)
    except BadSignature:
        return error("This reset link is invalid.", 400)

    user = db.session.get(User, payload["id"])
    if user is None or user.password_hash[-12:] != payload["p"]:
        return error("This reset link is invalid or was already used.", 400)

    user.set_password(password)
    db.session.commit()
    return jsonify({"message": "Your password has been changed."})


@bp.get("/me")
@jwt_required()
def me():
    return jsonify(current_user().to_dict())


@bp.patch("/me")
@jwt_required()
def update_me():
    user = current_user()
    data = json_body()
    fields = {}

    if "full_name" in data:
        name = str(data["full_name"] or "").strip()
        if len(name) < 2:
            fields["full_name"] = "Enter your full name."
        else:
            user.full_name = name
    if "phone" in data:
        phone = str(data["phone"] or "").strip()
        if len(phone) < 9:
            fields["phone"] = "Enter a valid phone number."
        else:
            user.phone = phone
    if "email" in data:
        email = str(data["email"] or "").strip().lower()
        taken = User.query.filter(User.email == email, User.id != user.id).first()
        if not is_email(email):
            fields["email"] = "Enter a valid email address."
        elif taken:
            fields["email"] = "This email is already registered."
        else:
            user.email = email
    if "email_notifications" in data:
        if isinstance(data["email_notifications"], bool):
            user.email_notifications = data["email_notifications"]
        else:
            fields["email_notifications"] = "Must be true or false."

    if fields:
        db.session.rollback()
        return error("Please fix the highlighted fields.", 400, fields=fields)
    db.session.commit()
    return jsonify(user.to_dict())
