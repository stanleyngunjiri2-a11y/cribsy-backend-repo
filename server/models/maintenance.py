"""OWNER: Member 6 (Lynn). Maintenance requests and their photos."""
from ..extensions import db
from .common import iso, utcnow


class MaintenanceRequest(db.Model):
    __tablename__ = "maintenance_requests"

    id = db.Column(db.Integer, primary_key=True)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancies.id"), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    tenancy = db.relationship("Tenancy", backref=db.backref("maintenance_requests", cascade="all, delete-orphan"))

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

    request = db.relationship("MaintenanceRequest", backref=db.backref("photos", cascade="all, delete-orphan"))
