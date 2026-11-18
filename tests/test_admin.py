"""OWNER: Member 6 (Lynn). Administrator tools: users and property approval."""
import pytest

from app.extensions import db
from tests.helpers import auth_header, make_property, make_user


@pytest.fixture()
def admin(app):
    return make_user("admin")


def test_only_admins_can_use_admin_routes(client):
    tenant = make_user("tenant")
    landlord = make_user("landlord")

    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/stats", headers=auth_header(tenant)).status_code == 403
    assert client.get("/api/admin/users", headers=auth_header(landlord)).status_code == 403


def test_stats(client, admin):
    landlord = make_user("landlord")
    make_user("tenant")
    make_property(landlord, approval_status="pending")

    data = client.get("/api/admin/stats", headers=auth_header(admin)).get_json()

    assert data["total_users"] == 3
    assert data["landlords"] == 1
    assert data["tenants"] == 1
    assert data["properties_pending_approval"] == 1


def test_filter_users_by_role_and_status(client, admin):
    landlord = make_user("landlord")
    make_user("tenant")
    make_user("tenant", status="suspended")
    headers = auth_header(admin)

    landlords = client.get("/api/admin/users?role=landlord", headers=headers).get_json()
    suspended = client.get("/api/admin/users?status=suspended", headers=headers).get_json()

    assert [u["id"] for u in landlords] == [landlord.id]
    assert len(suspended) == 1


def test_suspend_and_reactivate_a_user(client, admin):
    tenant = make_user("tenant")
    headers = auth_header(admin)

    suspended = client.patch(f"/api/admin/users/{tenant.id}/status", json={"status": "suspended"}, headers=headers)
    assert suspended.status_code == 200
    assert suspended.get_json()["status"] == "suspended"

    reactivated = client.patch(f"/api/admin/users/{tenant.id}/status", json={"status": "active"}, headers=headers)
    assert reactivated.get_json()["status"] == "active"


def test_a_suspended_user_is_locked_out_even_with_an_old_token(client, admin):
    landlord = make_user("landlord")
    old_token = auth_header(landlord)

    client.patch(f"/api/admin/users/{landlord.id}/status", json={"status": "suspended"}, headers=auth_header(admin))

    assert client.get("/api/landlord/properties", headers=old_token).status_code == 403


def test_admin_accounts_cannot_be_suspended(client, admin):
    other_admin = make_user("admin")
    headers = auth_header(admin)

    assert client.patch(f"/api/admin/users/{other_admin.id}/status", json={"status": "suspended"},
                        headers=headers).status_code == 403
    assert client.patch(f"/api/admin/users/{admin.id}/status", json={"status": "suspended"},
                        headers=headers).status_code == 403


def test_user_status_must_be_valid(client, admin):
    tenant = make_user("tenant")

    response = client.patch(f"/api/admin/users/{tenant.id}/status", json={"status": "banned"},
                            headers=auth_header(admin))

    assert response.status_code == 400


def test_list_properties_waiting_for_approval(client, admin):
    landlord = make_user("landlord")
    make_property(landlord, name="Waiting", approval_status="pending")
    make_property(landlord, name="Live", approval_status="approved")

    listing = client.get("/api/admin/properties?approval_status=pending", headers=auth_header(admin)).get_json()

    assert [p["name"] for p in listing] == ["Waiting"]
    assert listing[0]["landlord"]["full_name"] == landlord.full_name


def test_approving_a_property_makes_it_public(client, admin):
    prop = make_property(make_user("landlord"), approval_status="pending")
    assert client.get(f"/api/properties/{prop.id}").status_code == 404

    response = client.patch(f"/api/admin/properties/{prop.id}/approval", json={"approval_status": "approved"},
                            headers=auth_header(admin))

    assert response.status_code == 200
    db.session.refresh(prop)
    assert prop.approval_status == "approved"
    assert client.get(f"/api/properties/{prop.id}").status_code == 200


def test_rejecting_a_property_keeps_it_hidden(client, admin):
    prop = make_property(make_user("landlord"), approval_status="pending")

    client.patch(f"/api/admin/properties/{prop.id}/approval", json={"approval_status": "rejected"},
                 headers=auth_header(admin))

    assert client.get(f"/api/properties/{prop.id}").status_code == 404


def test_approval_value_must_be_valid(client, admin):
    prop = make_property(make_user("landlord"), approval_status="pending")

    response = client.patch(f"/api/admin/properties/{prop.id}/approval", json={"approval_status": "maybe"},
                            headers=auth_header(admin))

    assert response.status_code == 400
