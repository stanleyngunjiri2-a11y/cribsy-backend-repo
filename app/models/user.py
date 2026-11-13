"""OWNER: Member 1 (Stanley). Users and the one-time codes for two-step sign-in."""
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from .common import iso, utcnow


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="tenant")
    status = db.Column(db.String(20), nullable=False, default="active")
    email_notifications = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "status": self.status,
            "email_notifications": self.email_notifications,
            "created_at": iso(self.created_at),
        }


class VerificationCode(db.Model):
    """One-time code for the two-step sign-in."""

    __tablename__ = "verification_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship("User", backref=db.backref("verification_codes", cascade="all, delete-orphan"))
