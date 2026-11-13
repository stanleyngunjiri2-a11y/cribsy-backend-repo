"""Database models for RentConnect. See the diagram in README.md."""
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

# Allowed values (also useful for dropdowns on the frontend)
ROLES = ("tenant", "landlord", "admin")
USER_STATUSES = ("active", "suspended")
PROPERTY_TYPES = ("Apartment", "House", "Bedsitter", "Studio")
AVAILABILITY = ("vacant", "occupied")
APPROVALS = ("pending", "approved", "rejected")
TENANCY_STATUSES = ("active", "notice", "ended")
ACTIVE_TENANCY = ("active", "notice")  # a tenant still living in the property
PAYMENT_STATUSES = ("paid", "pending", "overdue")
PAYMENT_METHODS = ("Mobile money", "Bank transfer", "Cash")
MAINTENANCE_STATUSES = ("pending", "in_progress", "resolved", "rejected")
MAINTENANCE_CATEGORIES = (
    "Plumbing", "Electrical", "Appliances", "Doors and locks", "Pests", "Structural", "Other",
)


def utcnow():
    """Current UTC time without timezone info (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.isoformat() if value else None


# Many-to-many link table: a property has many amenities, an amenity is in many properties.
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
    phone = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="tenant")
    status = db.Column(db.String(20), nullable=False, default="active")
    email_notifications = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    properties = db.relationship("Property", back_populates="landlord")
    tenancies = db.relationship("Tenancy", back_populates="tenant")
    verification_codes = db.relationship(
        "VerificationCode", back_populates="user", cascade="all, delete-orphan"
    )

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

    user = db.relationship("User", back_populates="verification_codes")


class Amenity(db.Model):
    __tablename__ = "amenities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    properties = db.relationship("Property", secondary=property_amenities, back_populates="amenities")


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    landlord_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    property_type = db.Column(db.String(30), nullable=False)
    monthly_rent = db.Column(db.Integer, nullable=False)  # whole KSh
    bedrooms = db.Column(db.Integer, nullable=False)
    bathrooms = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    availability = db.Column(db.String(20), nullable=False, default="vacant")
    approval_status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    landlord = db.relationship("User", back_populates="properties")
    amenities = db.relationship("Amenity", secondary=property_amenities, back_populates="properties")
    tenancies = db.relationship("Tenancy", back_populates="property")
    enquiries = db.relationship("Enquiry", back_populates="property", cascade="all, delete-orphan")

    def to_dict(self, include_landlord=False):
        data = {
            "id": self.id,
            "landlord_id": self.landlord_id,
            "name": self.name,
            "location": self.location,
            "property_type": self.property_type,
            "monthly_rent": self.monthly_rent,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "description": self.description,
            "image_url": self.image_url,
            "availability": self.availability,
            "approval_status": self.approval_status,
            "amenities": sorted(a.name for a in self.amenities),
            "created_at": iso(self.created_at),
        }
        if include_landlord:
            data["landlord"] = {"id": self.landlord.id, "full_name": self.landlord.full_name}
        return data


class Enquiry(db.Model):
    __tablename__ = "enquiries"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    property = db.relationship("Property", back_populates="enquiries")

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "name": self.name,
            "email": self.email,
            "message": self.message,
            "created_at": iso(self.created_at),
        }


class Tenancy(db.Model):
    """A tenant renting a property for a period of time."""

    __tablename__ = "tenancies"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    monthly_rent = db.Column(db.Integer, nullable=False)

    tenant = db.relationship("User", back_populates="tenancies")
    property = db.relationship("Property", back_populates="tenancies")
    payments = db.relationship("RentPayment", back_populates="tenancy", cascade="all, delete-orphan")
    maintenance_requests = db.relationship(
        "MaintenanceRequest", back_populates="tenancy", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenant": {
                "id": self.tenant.id,
                "full_name": self.tenant.full_name,
                "email": self.tenant.email,
                "phone": self.tenant.phone,
            },
            "property": {
                "id": self.property.id,
                "name": self.property.name,
                "location": self.property.location,
                "property_type": self.property.property_type,
                "bedrooms": self.property.bedrooms,
                "bathrooms": self.property.bathrooms,
                "image_url": self.property.image_url,
                "landlord_name": self.property.landlord.full_name,
            },
            "start_date": iso(self.start_date),
            "end_date": iso(self.end_date),
            "status": self.status,
            "monthly_rent": self.monthly_rent,
        }


class RentPayment(db.Model):
    __tablename__ = "rent_payments"

    id = db.Column(db.Integer, primary_key=True)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancies.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    paid_on = db.Column(db.Date, nullable=False)
    reference = db.Column(db.String(60), unique=True, nullable=False)
    method = db.Column(db.String(30), nullable=False, default="Mobile money")
    status = db.Column(db.String(20), nullable=False, default="paid")

    tenancy = db.relationship("Tenancy", back_populates="payments")

    def to_dict(self):
        return {
            "id": self.id,
            "tenancy_id": self.tenancy_id,
            "tenant_name": self.tenancy.tenant.full_name,
            "property_name": self.tenancy.property.name,
            "amount": self.amount,
            "paid_on": iso(self.paid_on),
            "reference": self.reference,
            "method": self.method,
            "status": self.status,
        }


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.Integer, primary_key=True)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancies.id"), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    tenancy = db.relationship("Tenancy", back_populates="maintenance_requests")
    photos = db.relationship(
        "MaintenancePhoto", back_populates="request", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "tenancy_id": self.tenancy_id,
            "tenant_name": self.tenancy.tenant.full_name,
            "property_name": self.tenancy.property.name,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "photos": [p.file_url for p in self.photos],
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }


class MaintenancePhoto(db.Model):
    __tablename__ = "maintenance_photos"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("maintenance_requests.id"), nullable=False)
    file_url = db.Column(db.String(500), nullable=False)

    request = db.relationship("MaintenanceRequest", back_populates="photos")
