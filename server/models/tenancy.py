"""OWNER: Member 4 (Nato). A tenancy links one tenant to one property for a period of time."""
from ..extensions import db
from .common import iso


class Tenancy(db.Model):
    __tablename__ = "tenancies"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active")
    monthly_rent = db.Column(db.Integer, nullable=False)

    tenant = db.relationship("User", backref="tenancies")
    property = db.relationship("Property", backref="tenancies")

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