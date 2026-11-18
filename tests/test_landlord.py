"""OWNER: Member 4 (Nato). Landlord dashboard, own properties, tenants and tenancies."""
import pytest

from app.extensions import db
from app.models import Property, Tenancy
from tests.helpers import auth_header, make_payment, make_property, make_request, make_tenancy, make_user

NEW_PROPERTY = {
    "name": "Greenview Unit A2", "location": "Ruiru, Kiambu", "property_type": "Apartment",
    "monthly_rent": 28000, "bedrooms": 2, "bathrooms": 1,
    "description": "Two bedroom apartment with parking.", "availability": "vacant",
    "amenities": ["Parking", "Water supply"],
}


@pytest.fixture()
def landlord(app):
    return make_user("landlord")


def assign(client, landlord, tenant, prop, **overrides):
    payload = {"tenant_email": tenant.email, "property_id": prop.id,
               "start_date": "2026-11-01", "end_date": "2027-10-31", **overrides}
    return client.post("/api/landlord/tenancies", json=payload, headers=auth_header(landlord))


# ----- access -----
def test_landlord_routes_need_sign_in(client):
    assert client.get("/api/landlord/properties").status_code == 401


def test_a_tenant_cannot_use_landlord_routes(client):
    tenant = make_user("tenant")

    assert client.get("/api/landlord/properties", headers=auth_header(tenant)).status_code == 403


# ----- properties -----
def test_a_new_property_waits_for_approval(client, landlord):
    response = client.post("/api/landlord/properties", json=NEW_PROPERTY, headers=auth_header(landlord))

    assert response.status_code == 201
    body = response.get_json()
    assert body["approval_status"] == "pending"
    assert body["amenities"] == ["Parking", "Water supply"]
    assert Property.query.count() == 1


def test_a_new_property_reports_invalid_fields(client, landlord):
    response = client.post("/api/landlord/properties", json={}, headers=auth_header(landlord))

    assert response.status_code == 400
    expected = {"name", "location", "property_type", "monthly_rent", "bedrooms", "bathrooms", "description"}
    assert expected <= set(response.get_json()["fields"])


def test_a_landlord_only_sees_their_own_properties(client, landlord):
    make_property(landlord, name="Mine")
    make_property(make_user("landlord"), name="Not mine")

    response = client.get("/api/landlord/properties", headers=auth_header(landlord))

    assert [p["name"] for p in response.get_json()] == ["Mine"]


def test_update_own_property(client, landlord):
    prop = make_property(landlord, monthly_rent=20000)

    response = client.put(f"/api/landlord/properties/{prop.id}", json={**NEW_PROPERTY, "monthly_rent": 25000},
                          headers=auth_header(landlord))

    assert response.status_code == 200
    db.session.refresh(prop)
    assert prop.monthly_rent == 25000


def test_another_landlords_property_is_hidden(client, landlord):
    theirs = make_property(make_user("landlord"))
    headers = auth_header(landlord)

    assert client.get(f"/api/landlord/properties/{theirs.id}", headers=headers).status_code == 404
    assert client.put(f"/api/landlord/properties/{theirs.id}", json=NEW_PROPERTY, headers=headers).status_code == 404
    assert client.delete(f"/api/landlord/properties/{theirs.id}", headers=headers).status_code == 404


def test_delete_a_property(client, landlord):
    prop = make_property(landlord)

    response = client.delete(f"/api/landlord/properties/{prop.id}", headers=auth_header(landlord))

    assert response.status_code == 204
    assert Property.query.count() == 0


def test_a_property_with_tenancy_history_cannot_be_deleted(client, landlord):
    prop = make_property(landlord)
    make_tenancy(make_user("tenant"), prop)

    response = client.delete(f"/api/landlord/properties/{prop.id}", headers=auth_header(landlord))

    assert response.status_code == 409
    assert Property.query.count() == 1


# ----- dashboard -----
def test_dashboard_numbers(client, landlord):
    tenant = make_user("tenant")
    occupied = make_property(landlord, name="Occupied")
    make_property(landlord, name="Vacant")
    tenancy = make_tenancy(tenant, occupied)
    make_request(tenancy, status="pending")
    make_payment(tenancy)

    data = client.get("/api/landlord/dashboard", headers=auth_header(landlord)).get_json()

    assert data["total_properties"] == 2
    assert data["occupied_properties"] == 1
    assert data["vacant_properties"] == 1
    assert data["registered_tenants"] == 1
    assert data["pending_maintenance"] == 1
    assert len(data["recent_payments"]) == 1


def test_dashboard_for_a_new_landlord_is_all_zeros(client, landlord):
    data = client.get("/api/landlord/dashboard", headers=auth_header(landlord)).get_json()

    assert data["total_properties"] == 0
    assert data["recent_payments"] == []


# ----- assigning tenants -----
def test_assign_a_tenant_to_a_vacant_property(client, landlord):
    tenant = make_user("tenant")
    prop = make_property(landlord)

    response = assign(client, landlord, tenant, prop)

    assert response.status_code == 201
    assert response.get_json()["monthly_rent"] == prop.monthly_rent
    db.session.refresh(prop)
    assert prop.availability == "occupied"
    assert Tenancy.query.count() == 1


def test_assign_fails_when_the_tenant_has_no_account(client, landlord):
    prop = make_property(landlord)

    response = client.post("/api/landlord/tenancies", headers=auth_header(landlord), json={
        "tenant_email": "nobody@test.com", "property_id": prop.id,
        "start_date": "2026-11-01", "end_date": "2027-10-31"})

    assert response.status_code == 404


def test_assign_fails_when_the_property_is_not_vacant(client, landlord):
    prop = make_property(landlord, availability="occupied")

    assert assign(client, landlord, make_user("tenant"), prop).status_code == 409


def test_assign_fails_when_the_property_is_not_approved(client, landlord):
    prop = make_property(landlord, approval_status="pending")

    assert assign(client, landlord, make_user("tenant"), prop).status_code == 409


def test_a_tenant_cannot_have_two_active_tenancies(client, landlord):
    tenant = make_user("tenant")
    make_tenancy(tenant, make_property(landlord, name="First"))
    second = make_property(landlord, name="Second")

    assert assign(client, landlord, tenant, second).status_code == 409


def test_assign_rejects_an_end_date_before_the_start_date(client, landlord):
    prop = make_property(landlord)

    response = assign(client, landlord, make_user("tenant"), prop, start_date="2026-11-01", end_date="2026-10-01")

    assert response.status_code == 400
    assert "end_date" in response.get_json()["fields"]


def test_assign_to_another_landlords_property_is_404(client, landlord):
    theirs = make_property(make_user("landlord"))

    assert assign(client, landlord, make_user("tenant"), theirs).status_code == 404


def test_ending_a_tenancy_makes_the_property_vacant(client, landlord):
    prop = make_property(landlord)
    tenancy = make_tenancy(make_user("tenant"), prop)

    response = client.patch(f"/api/landlord/tenancies/{tenancy.id}", json={"status": "ended"},
                            headers=auth_header(landlord))

    assert response.status_code == 200
    db.session.refresh(prop)
    assert prop.availability == "vacant"


def test_tenancy_status_must_be_valid(client, landlord):
    tenancy = make_tenancy(make_user("tenant"), make_property(landlord))

    response = client.patch(f"/api/landlord/tenancies/{tenancy.id}", json={"status": "banana"},
                            headers=auth_header(landlord))

    assert response.status_code == 400


# ----- tenants list -----
def test_tenants_list_hides_past_tenants_unless_asked(client, landlord):
    current = make_tenancy(make_user("tenant"), make_property(landlord, name="Now"))
    make_tenancy(make_user("tenant"), make_property(landlord, name="Before"), status="ended")
    headers = auth_header(landlord)

    default = client.get("/api/landlord/tenants", headers=headers).get_json()
    everyone = client.get("/api/landlord/tenants?include_ended=true", headers=headers).get_json()

    assert [t["id"] for t in default] == [current.id]
    assert len(everyone) == 2