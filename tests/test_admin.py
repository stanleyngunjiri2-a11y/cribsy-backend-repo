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
    make_user("tenant", status="suspended")
    make_user("admin")
    make_user("superadmin")
    make_property(landlord, approval_status="pending")
    make_property(landlord, approval_status="approved")
    make_property(landlord, approval_status="rejected")

    data = client.get("/api/admin/stats", headers=auth_header(admin)).get_json()

    assert data["total_users"] == 6
    assert data["landlords"] == 1
    assert data["tenants"] == 2
    assert data["administrators"] == 2
    assert data["superadmins"] == 1
    assert data["active_users"] == 5
    assert data["suspended_users"] == 1
    assert data["total_properties"] == 3
    assert data["properties_pending_approval"] == 1
    assert data["properties_approved"] == 1
    assert data["properties_rejected"] == 1


def test_superadmins_can_use_admin_routes(client):
    superadmin = make_user("superadmin")

    assert client.get("/api/admin/stats", headers=auth_header(superadmin)).status_code == 200
    assert client.get("/api/admin/properties", headers=auth_header(superadmin)).status_code == 200


def test_only_superadmins_can_view_and_manage_administrator_accounts(client, admin):
    other_admin = make_user("admin")
    superadmin = make_user("superadmin")
    superadmin_headers = auth_header(superadmin)

    assert client.get("/api/admin/users?role=admin", headers=auth_header(admin)).status_code == 403
    assert client.get("/api/admin/users?role=superadmin", headers=auth_header(admin)).status_code == 403
    listed_admins = client.get("/api/admin/users?role=admin", headers=superadmin_headers).get_json()
    assert {user["id"] for user in listed_admins} == {admin.id, other_admin.id}

    assert client.patch(
        f"/api/admin/users/{other_admin.id}/status",
        json={"status": "suspended"},
        headers=auth_header(admin),
    ).status_code == 403
    response = client.patch(
        f"/api/admin/users/{other_admin.id}/status",
        json={"status": "suspended"},
        headers=superadmin_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "suspended"


def test_superadmins_cannot_suspend_themselves_or_another_superadmin(client):
    superadmin = make_user("superadmin")
    other_superadmin = make_user("superadmin")
    headers = auth_header(superadmin)

    assert client.patch(
        f"/api/admin/users/{superadmin.id}/status",
        json={"status": "suspended"},
        headers=headers,
    ).status_code == 403
    assert client.patch(
        f"/api/admin/users/{other_superadmin.id}/status",
        json={"status": "suspended"},
        headers=headers,
    ).status_code == 403


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


def test_superadmin_can_view_a_nonpublic_property(client):
    prop = make_property(make_user("landlord"), approval_status="rejected")

    response = client.get(
        f"/api/properties/{prop.id}",
        headers=auth_header(make_user("superadmin")),
    )

    assert response.status_code == 200


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
