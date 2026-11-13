
from datetime import datetime, timezone

from server.extension import db


def utcnow():
    return datetime.now(timezone.utc)


class Enquiry(db.Model):
    __tablename__ = "enquiries"

    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    
    property = db.relationship(
        "Property",
        backref=db.backref("enquiries", cascade="all, delete-orphan"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "property_id": self.property_id,
            "name": self.name,
            "email": self.email,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }