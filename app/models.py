from datetime import datetime

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()

property_amenities = db.Table(
    "property_amenities",
    db.Column("property_id", db.Integer, db.ForeignKey("properties.id"), primary_key=True),
    db.Column("amenity_id", db.Integer, db.ForeignKey("amenities.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="tenant")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    verification_codes = db.relationship("VerificationCode", back_populates="user", cascade="all, delete-orphan")
    properties = db.relationship("Property", back_populates="landlord", cascade="all, delete-orphan")
    tenancies = db.relationship("Tenancy", back_populates="tenant")


class VerificationCode(db.Model):
    __tablename__ = "verification_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    code = db.Column(db.String(10), nullable=False)
    purpose = db.Column(db.String(30), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="verification_codes")


class Amenity(db.Model):
    __tablename__ = "amenities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    landlord_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False, index=True)
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    property_type = db.Column(db.String(40), nullable=False)
    bedrooms = db.Column(db.Integer, nullable=False, default=0)
    bathrooms = db.Column(db.Numeric(3, 1), nullable=False, default=1)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=False)
    is_available = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    landlord = db.relationship("User", back_populates="properties")
    amenities = db.relationship("Amenity", secondary=property_amenities, backref="properties")
    enquiries = db.relationship("Enquiry", back_populates="property", cascade="all, delete-orphan")
    tenancies = db.relationship("Tenancy", back_populates="property")


class Enquiry(db.Model):
    __tablename__ = "enquiries"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    property = db.relationship("Property", back_populates="enquiries")
    tenant = db.relationship("User")


class Tenancy(db.Model):
    __tablename__ = "tenancies"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    property = db.relationship("Property", back_populates="tenancies")
    tenant = db.relationship("User", back_populates="tenancies")
    rent_payments = db.relationship("RentPayment", back_populates="tenancy", cascade="all, delete-orphan")
    maintenance_requests = db.relationship("MaintenanceRequest", back_populates="tenancy", cascade="all, delete-orphan")


class RentPayment(db.Model):
    __tablename__ = "rent_payments"

    id = db.Column(db.Integer, primary_key=True)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancies.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="pending")
    reference = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tenancy = db.relationship("Tenancy", back_populates="rent_payments")


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.Integer, primary_key=True)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancies.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="normal")
    status = db.Column(db.String(20), nullable=False, default="open", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenancy = db.relationship("Tenancy", back_populates="maintenance_requests")
    photos = db.relationship("MaintenancePhoto", back_populates="maintenance_request", cascade="all, delete-orphan")


class MaintenancePhoto(db.Model):
    __tablename__ = "maintenance_photos"

    id = db.Column(db.Integer, primary_key=True)
    maintenance_request_id = db.Column(
        db.Integer,
        db.ForeignKey("maintenance_requests.id"),
        nullable=False,
        index=True,
    )
    photo_url = db.Column(db.String(2048), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    maintenance_request = db.relationship("MaintenanceRequest", back_populates="photos")
