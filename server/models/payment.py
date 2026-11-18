from ..extension import db
from .common import iso


class RentPayment(db.Model):
    __tablename__ = "rent_payments"

    id = db.Column(db.Integer, primary_key=True)
    tenancy_id = db.Column(db.Integer, db.ForeignKey("tenancies.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    paid_on = db.Column(db.Date, nullable=False)
    reference = db.Column(db.String(60), unique=True, nullable=False)
    method = db.Column(db.String(30), nullable=False, default="Mobile money")
    status = db.Column(db.String(20), nullable=False, default="paid")

    tenancy = db.relationship("Tenancy", backref=db.backref("payments", cascade="all, delete-orphan"))

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
