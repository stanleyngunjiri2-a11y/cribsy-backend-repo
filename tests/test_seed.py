
from app.models import MaintenanceRequest, Property, RentPayment, Tenancy, User
from seed import seed


def test_seed_adds_the_sample_data(app):
    seed(app)

    assert User.query.count() == 5
    assert User.query.filter_by(email="admin@rentconnect.test", role="admin").count() == 1
    assert Property.query.filter_by(approval_status="approved").count() == 8
    assert Property.query.filter_by(approval_status="pending").count() == 2
    assert Tenancy.query.count() == 3
    assert RentPayment.query.count() == 7
    assert MaintenanceRequest.query.count() == 3


def test_seed_can_sign_in(app, client):
    seed(app)

    response = client.post("/api/auth/login", json={"email": "landlord@rentconnect.test", "password": "Landlord123"})

    assert response.status_code == 200


def test_running_seed_twice_does_not_duplicate_anything(app):
    seed(app)
    seed(app)

    assert User.query.count() == 5
    assert Property.query.count() == 10
