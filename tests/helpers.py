"""OWNER: Member 1 (Stanley). Small functions that create test data. Every test file uses them.

Models are imported inside the functions, so this file works even before every member has pushed their model.
"""
import itertools
from datetime import date

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User

PASSWORD = "Passw0rd1"
_counter = itertools.count(1)


def make_user(role="tenant", status="active"):
    number = next(_counter)
    user = User(full_name=f"{role.title()} {number}", email=f"{role}{number}@test.com",
                phone="0712345678", role=role, status=status)
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user


def auth_header(user):
    """A ready-made Authorization header, so a test does not have to go through the two-step sign-in."""
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return {"Authorization": f"Bearer {token}"}


def make_property(landlord, **overrides):
    from app.models import Property

    values = dict(name="Test House", location="Ruiru, Kiambu", property_type="House", monthly_rent=30000,
                  bedrooms=2, bathrooms=1, description="A nice test property.",
                  availability="vacant", approval_status="approved")
    values.update(overrides)
    prop = Property(landlord_id=landlord.id, **values)
    db.session.add(prop)
    db.session.commit()
    return prop


def make_tenancy(tenant, prop, status="active"):
    from app.models import Tenancy

    tenancy = Tenancy(tenant_id=tenant.id, property_id=prop.id, start_date=date(2026, 1, 1),
                      end_date=date(2026, 12, 31), status=status, monthly_rent=prop.monthly_rent)
    prop.availability = "vacant" if status == "ended" else "occupied"
    db.session.add(tenancy)
    db.session.commit()
    return tenancy


def make_payment(tenancy, paid_on=date(2026, 11, 2), status="paid", reference=None):
    from app.models import RentPayment

    payment = RentPayment(tenancy_id=tenancy.id, amount=tenancy.monthly_rent, paid_on=paid_on,
                          reference=reference or f"REF-{next(_counter)}", status=status)
    db.session.add(payment)
    db.session.commit()
    return payment


def make_request(tenancy, category="Plumbing", status="pending"):
    from app.models import MaintenanceRequest

    row = MaintenanceRequest(tenancy_id=tenancy.id, category=category,
                             description="The kitchen tap is leaking badly.", status=status)
    db.session.add(row)
    db.session.commit()
    return row
