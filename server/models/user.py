from werkzeug.security import generate_password_hash, check_password_hash
from ..extension import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.String(20), nullable=False, default="tenant"
    )  # 'admin', 'landlord', 'tenant'
    status = db.Column(
        db.String(20), nullable=False, default="active"
    )  # 'active', 'suspended'
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    properties = db.relationship("Property", backref="landlord", lazy=True)

    # Password management
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "status": self.status,
        }
