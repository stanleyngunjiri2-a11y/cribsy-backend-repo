from datetime import datetime, timezone

from app.extensions import db
from app.models import Enquiry, Property, User, utcnow


def create_property():
    landlord = User(
        full_name="Test Landlord",
        email="landlord@example.com",
        phone="0712345678",
        password_hash="test-hash",
        role="landlord",
    )
    property_record = Property(
        landlord=landlord,
        name="Test Apartment",
        location="Nairobi",
        property_type="Apartment",
        monthly_rent=25000,
        bedrooms=2,
        bathrooms=1,
        description="Test property",
    )
    return property_record


def test_utcnow_returns_naive_utc_datetime():
    result = utcnow()

    assert isinstance(result, datetime)
    assert result.tzinfo is None


def test_to_dict_serializes_enquiry_fields_and_timestamp():
    created_at = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)
    enquiry = Enquiry(
        id=12,
        property_id=4,
        name="Avery",
        email="avery@example.com",
        message="Is this property available?",
        created_at=created_at,
    )

    assert enquiry.to_dict() == {
        "id": 12,
        "property_id": 4,
        "name": "Avery",
        "email": "avery@example.com",
        "message": "Is this property available?",
        "created_at": "2026-11-13T08:00:00+00:00",
    }


def test_to_dict_returns_none_for_missing_timestamp():
    enquiry = Enquiry(
        property_id=4,
        name="Avery",
        email="avery@example.com",
        message="Is this property available?",
    )

    assert enquiry.to_dict()["created_at"] is None


def test_created_at_uses_default_when_record_is_saved(app):
    with app.app_context():
        property_record = create_property()
        enquiry = Enquiry(
            property=property_record,
            name="Avery",
            email="avery@example.com",
            message="Is this property available?",
        )
        db.session.add(enquiry)
        db.session.commit()

        assert isinstance(enquiry.created_at, datetime)
