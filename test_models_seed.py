import importlib
import sys
import types
from datetime import date, datetime

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy


# The repository currently has no app factory or extensions module.
db = SQLAlchemy()
extensions = types.ModuleType("app.extensions")
extensions.db = db
sys.modules["app.extensions"] = extensions

app_package = importlib.import_module("app")
models = importlib.import_module("app.models")

test_app = Flask(__name__)
test_app.config.update(
    SQLALCHEMY_DATABASE_URI="sqlite://",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db.init_app(test_app)
app_package.create_app = lambda: test_app
seed = importlib.import_module("seed")


@pytest.fixture(autouse=True)
def database():
    with test_app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def make_user(**overrides):
    values = {
        "full_name": "Test Landlord",
        "email": "landlord@example.test",
        "phone": "0700000000",
        "role": "landlord",
    }
    values.update(overrides)
    user = models.User(**values)
    user.set_password("correct horse battery staple")
    return user


def make_property(landlord, **overrides):
    values = {
        "landlord": landlord,
        "name": "Greenview",
        "location": "Nairobi",
        "property_type": "Apartment",
        "monthly_rent": 28000,
        "bedrooms": 2,
        "bathrooms": 1,
        "description": "Bright apartment",
    }
    values.update(overrides)
    return models.Property(**values)


def test_model_helpers_and_user_password_serialization():
    now = models.utcnow()
    assert now.tzinfo is None
    assert models.iso(None) is None
    assert models.iso(now) == now.isoformat()
    assert models.ROLES == ("tenant", "landlord", "admin")
    assert models.USER_STATUSES == ("active", "suspended")
    assert models.PROPERTY_TYPES == ("Apartment", "House", "Bedsitter", "Studio")
    assert models.AVAILABILITY == ("vacant", "occupied")
    assert models.APPROVALS == ("pending", "approved", "rejected")
    assert models.TENANCY_STATUSES == ("active", "notice", "ended")
    assert models.ACTIVE_TENANCY == ("active", "notice")
    assert models.PAYMENT_STATUSES == ("paid", "pending", "overdue")
    assert models.PAYMENT_METHODS == ("Mobile money", "Bank transfer", "Cash")
    assert models.MAINTENANCE_STATUSES == ("pending", "in_progress", "resolved", "rejected")
    assert models.MAINTENANCE_CATEGORIES == (
        "Plumbing", "Electrical", "Appliances", "Doors and locks", "Pests", "Structural", "Other",
    )

    user = make_user()
    db.session.add(user)
    db.session.commit()

    assert user.check_password("correct horse battery staple")
    assert not user.check_password("wrong password")
    assert user.to_dict() == {
        "id": user.id,
        "full_name": "Test Landlord",
        "email": "landlord@example.test",
        "phone": "0700000000",
        "role": "landlord",
        "status": "active",
        "email_notifications": True,
        "created_at": user.created_at.isoformat(),
    }
    assert "password_hash" not in user.to_dict()


def test_property_amenity_and_enquiry_serialization():
    landlord = make_user()
    property_ = make_property(landlord)
    property_.amenities.extend([models.Amenity(name="Water"), models.Amenity(name="Parking")])
    enquiry = models.Enquiry(
        name="Jane",
        email="jane@example.test",
        message="Is this property available?",
        property=property_,
    )
    db.session.add_all([landlord, property_, enquiry])
    db.session.commit()

    property_data = property_.to_dict()
    assert property_data["amenities"] == ["Parking", "Water"]
    assert property_data["created_at"] == property_.created_at.isoformat()
    assert "landlord" not in property_data
    assert property_.to_dict(include_landlord=True)["landlord"] == {
        "id": landlord.id,
        "full_name": landlord.full_name,
    }
    assert property_.availability == "vacant"
    assert property_.approval_status == "pending"
    assert property_.amenities[0].properties == [property_]
    assert enquiry.to_dict() == {
        "id": enquiry.id,
        "property_id": property_.id,
        "name": "Jane",
        "email": "jane@example.test",
        "message": "Is this property available?",
        "created_at": enquiry.created_at.isoformat(),
    }


def test_tenancy_payment_and_verification_code_serialization():
    landlord = make_user()
    tenant = make_user(full_name="Jane Tenant", email="jane@example.test", role="tenant")
    property_ = make_property(landlord)
    tenancy = models.Tenancy(
        tenant=tenant,
        property=property_,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=28000,
    )
    payment = models.RentPayment(
        tenancy=tenancy,
        amount=28000,
        paid_on=date(2026, 2, 1),
        reference="PAY-1",
    )
    code = models.VerificationCode(
        user=tenant,
        code_hash="hashed-code",
        expires_at=datetime(2026, 1, 2),
    )
    db.session.add_all([landlord, tenant, property_, tenancy, payment, code])
    db.session.commit()

    assert code.used is False
    assert tenant.verification_codes == [code]
    assert tenancy.to_dict() == {
        "id": tenancy.id,
        "tenant": {
            "id": tenant.id,
            "full_name": "Jane Tenant",
            "email": "jane@example.test",
            "phone": tenant.phone,
        },
        "property": {
            "id": property_.id,
            "name": property_.name,
            "location": property_.location,
            "property_type": property_.property_type,
            "bedrooms": property_.bedrooms,
            "bathrooms": property_.bathrooms,
            "image_url": property_.image_url,
            "landlord_name": landlord.full_name,
        },
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "status": "active",
        "monthly_rent": 28000,
    }
    assert payment.method == "Mobile money"
    assert payment.status == "paid"
    assert payment.to_dict() == {
        "id": payment.id,
        "tenancy_id": tenancy.id,
        "tenant_name": tenant.full_name,
        "property_name": property_.name,
        "amount": 28000,
        "paid_on": "2026-02-01",
        "reference": "PAY-1",
        "method": "Mobile money",
        "status": "paid",
    }


def test_maintenance_request_photo_serialization_and_cascades():
    landlord = make_user()
    tenant = make_user(full_name="Jane Tenant", email="jane@example.test", role="tenant")
    property_ = make_property(landlord)
    tenancy = models.Tenancy(
        tenant=tenant,
        property=property_,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        monthly_rent=28000,
    )
    request = models.MaintenanceRequest(
        tenancy=tenancy,
        category="Plumbing",
        description="Leaking tap",
    )
    photo = models.MaintenancePhoto(file_url="https://example.test/leak.jpg")
    request.photos.append(photo)
    enquiry = models.Enquiry(
        property=property_,
        name="Jane",
        email="jane@example.test",
        message="Question",
    )
    code = models.VerificationCode(
        user=tenant,
        code_hash="hashed-code",
        expires_at=datetime(2026, 1, 2),
    )
    db.session.add_all([landlord, tenant, property_, tenancy, request, enquiry, code])
    db.session.commit()

    assert request.status == "pending"
    assert request.updated_at is not None
    assert request.to_dict() == {
        "id": request.id,
        "tenancy_id": tenancy.id,
        "tenant_name": tenant.full_name,
        "property_name": property_.name,
        "category": "Plumbing",
        "description": "Leaking tap",
        "status": "pending",
        "photos": ["https://example.test/leak.jpg"],
        "created_at": request.created_at.isoformat(),
        "updated_at": request.updated_at.isoformat(),
    }
    assert photo.request is request

    code_owner = make_user(full_name="Code Owner", email="code@example.test", role="tenant")
    code.user = code_owner
    db.session.add(code_owner)
    db.session.commit()
    db.session.delete(code_owner)
    db.session.delete(tenancy)
    db.session.commit()
    assert models.VerificationCode.query.count() == 0
    assert models.Tenancy.query.count() == 0
    assert models.RentPayment.query.count() == 0
    assert models.MaintenanceRequest.query.count() == 0
    assert models.MaintenancePhoto.query.count() == 0
    assert models.Enquiry.query.count() == 1


def test_seed_populates_sample_data_and_is_idempotent(capsys):
    seed.seed()
    assert "Sample data added." in capsys.readouterr().out
    assert models.User.query.count() == 5
    assert models.Property.query.count() == 10
    assert models.Amenity.query.count() == 7
    assert models.Tenancy.query.count() == 3
    assert models.RentPayment.query.count() == 7
    assert models.MaintenanceRequest.query.count() == 3
    assert models.MaintenancePhoto.query.count() == 1
    assert models.Enquiry.query.count() == 0

    pending = {
        property_.name
        for property_ in models.Property.query.filter_by(approval_status="pending").all()
    }
    assert pending == {"Maple Court Studio", "Lakeview Bedsitter"}
    assert models.Property.query.filter_by(availability="occupied").count() == 3
    assert models.User.query.filter_by(email="admin@rentconnect.test").first().check_password(
        seed.PASSWORDS["admin"]
    )

    seed.seed()
    assert "already has users" in capsys.readouterr().out
    assert models.User.query.count() == 5
    assert models.Property.query.count() == 10
