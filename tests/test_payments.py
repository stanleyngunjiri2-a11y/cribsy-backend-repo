from datetime import date

import pytest

from app.extensions import db
from app.models import RentPayment
from tests.helpers import auth_header, make_payment, make_property, make_tenancy, make_user


@pytest.fixture()
def setup(app):
    """One landlord, one tenant renting one property."""
    landlord = make_user("landlord")
    tenant = make_user("tenant")
    prop = make_property(landlord, name="Greenview")
    tenancy = make_tenancy(tenant, prop)
    return landlord, tenant, tenancy


def record(client, landlord, tenancy, **body):
    body.setdefault("amount", 28000)
    return client.post(f"/api/landlord/tenancies/{tenancy.id}/payments", json=body, headers=auth_header(landlord))


# ----- landlord records payments -----
def test_record_a_payment(client, setup):
    landlord, _, tenancy = setup

    response = record(client, landlord, tenancy)

    assert response.status_code == 201
    body = response.get_json()
    assert body["reference"].startswith("RC-")  # made automatically
    assert body["status"] == "paid"
    assert RentPayment.query.count() == 1


def test_a_payment_needs_a_valid_amount(client, setup):
    landlord, _, tenancy = setup

    for bad in (0, -5, "abc"):
        response = record(client, landlord, tenancy, amount=bad)
        assert response.status_code == 400
        assert "amount" in response.get_json()["fields"]


def test_a_payment_reference_must_be_unique(client, setup):
    landlord, _, tenancy = setup

    assert record(client, landlord, tenancy, reference="MPESA123").status_code == 201
    again = record(client, landlord, tenancy, reference="MPESA123")

    assert again.status_code == 400
    assert "reference" in again.get_json()["fields"]


def test_a_payment_needs_a_valid_status_and_method(client, setup):
    landlord, _, tenancy = setup

    response = record(client, landlord, tenancy, status="maybe", method="Barter")

    assert response.status_code == 400
    assert {"status", "method"} <= set(response.get_json()["fields"])


def test_a_landlord_cannot_record_a_payment_for_someone_elses_tenant(client, setup):
    _, _, tenancy = setup
    stranger = make_user("landlord")

    assert record(client, stranger, tenancy).status_code == 404


def test_landlord_payment_list_is_newest_first(client, setup):
    landlord, _, tenancy = setup
    make_payment(tenancy, paid_on=date(2026, 9, 1), reference="OLD")
    make_payment(tenancy, paid_on=date(2026, 11, 1), reference="NEW")

    response = client.get("/api/landlord/payments", headers=auth_header(landlord))

    assert [p["reference"] for p in response.get_json()] == ["NEW", "OLD"]


def test_update_a_payment_status(client, setup):
    landlord, _, tenancy = setup
    payment = make_payment(tenancy, status="pending")

    response = client.patch(f"/api/landlord/payments/{payment.id}", json={"status": "paid"},
                            headers=auth_header(landlord))

    assert response.status_code == 200
    db.session.refresh(payment)
    assert payment.status == "paid"


def test_update_a_payment_with_an_invalid_status(client, setup):
    landlord, _, tenancy = setup
    payment = make_payment(tenancy)

    response = client.patch(f"/api/landlord/payments/{payment.id}", json={"status": "banana"},
                            headers=auth_header(landlord))

    assert response.status_code == 400


# ----- tenant side -----
def test_a_tenant_only_sees_their_own_payments(client, setup):
    _, tenant, tenancy = setup
    make_payment(tenancy, reference="MINE")
    other_tenancy = make_tenancy(make_user("tenant"), make_property(make_user("landlord"), name="Elsewhere"))
    make_payment(other_tenancy, reference="THEIRS")

    response = client.get("/api/tenant/payments", headers=auth_header(tenant))

    assert [p["reference"] for p in response.get_json()] == ["MINE"]


def test_payment_details(client, setup):
    _, tenant, tenancy = setup
    payment = make_payment(tenancy, reference="MINE")

    response = client.get(f"/api/tenant/payments/{payment.id}", headers=auth_header(tenant))

    assert response.status_code == 200
    assert response.get_json()["reference"] == "MINE"
    assert response.get_json()["property_name"] == "Greenview"


def test_another_tenants_payment_is_hidden(client, setup):
    _, _, tenancy = setup
    payment = make_payment(tenancy)
    stranger = make_user("tenant")

    assert client.get(f"/api/tenant/payments/{payment.id}", headers=auth_header(stranger)).status_code == 404


def test_the_tenant_dashboard(client, setup):
    _, tenant, tenancy = setup
    for day in range(1, 6):
        make_payment(tenancy, paid_on=date(2026, 6, day))

    data = client.get("/api/tenant/dashboard", headers=auth_header(tenant)).get_json()

    assert data["tenancy"]["property"]["name"] == "Greenview"
    assert len(data["recent_payments"]) == 3  # only the latest three
    assert data["maintenance_requests"] == []


def test_a_tenant_without_a_home_gets_an_empty_tenancy(client, app):
    tenant = make_user("tenant")

    response = client.get("/api/tenant/tenancy", headers=auth_header(tenant))

    assert response.status_code == 200
    assert response.get_json() == {"tenancy": None}


def test_a_landlord_cannot_use_tenant_routes(client, setup):
    landlord, _, _ = setup

    assert client.get("/api/tenant/payments", headers=auth_header(landlord)).status_code == 403
