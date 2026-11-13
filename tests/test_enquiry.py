from datetime import datetime, timezone

import pytest
from flask import Flask

from server.extension import db
from server.models.enquiry import Enquiry, utcnow


class Property(db.Model):
    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_utcnow_returns_utc_datetime():
    result = utcnow()

    assert result.tzinfo is timezone.utc


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
        property_record = Property()
        enquiry = Enquiry(
            property=property_record,
            name="Avery",
            email="avery@example.com",
            message="Is this property available?",
        )
        db.session.add(enquiry)
        db.session.commit()

        assert isinstance(enquiry.created_at, datetime)
