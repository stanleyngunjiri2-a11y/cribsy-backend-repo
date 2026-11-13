"""OWNER: Member 3 (Quincy). Properties and their amenities (a many-to-many relationship)."""
from ..extensions import db
from .common import iso, utcnow

# Link table: a property has many amenities, an amenity belongs to many properties.
property_amenities = db.Table(
    "property_amenities",
    db.Column("property_id", db.Integer, db.ForeignKey("properties.id"), primary_key=True),
    db.Column("amenity_id", db.Integer, db.ForeignKey("amenities.id"), primary_key=True),
)


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

    landlord = db.relationship("User", backref="properties")
    amenities = db.relationship("Amenity", secondary=property_amenities, back_populates="properties")

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
