"""OWNER: Member 6 (Lynn). Maintenance requests from the tenant and landlord sides."""
import pytest

from app.extensions import db
from app.models import MaintenanceRequest
from tests.helpers import auth_header, make_property, make_request, make_tenancy, make_user

REQUEST = {"category": "Plumbing", "description": "The kitchen tap has been leaking for three days."}


@pytest.fixture()
def setup(app):
    landlord = make_user("landlord")
    tenant = make_user("tenant")
    tenancy = make_tenancy(tenant, make_property(landlord))
    return landlord, tenant, tenancy


# ----- tenant side -----
def test_a_tenant_can_report_an_issue(client, setup):
    _, tenant, _ = setup

    response = client.post("/api/tenant/maintenance", json=REQUEST, headers=auth_header(tenant))

    assert response.status_code == 201
    assert response.get_json()["status"] == "pending"
    assert MaintenanceRequest.query.count() == 1


def test_a_request_can_include_photo_links(client, setup):
    _, tenant, _ = setup

    response = client.post("/api/tenant/maintenance", headers=auth_header(tenant),
                           json={**REQUEST, "photo_urls": ["https://example.com/one.jpg"]})

    assert response.status_code == 201
    assert response.get_json()["photos"] == ["https://example.com/one.jpg"]


def test_a_request_reports_invalid_fields(client, setup):
    _, tenant, _ = setup

    response = client.post("/api/tenant/maintenance", json={"category": "Magic", "description": "short"},
                           headers=auth_header(tenant))

    assert response.status_code == 400
    assert {"category", "description"} <= set(response.get_json()["fields"])


def test_at_most_four_photos(client, setup):
    _, tenant, _ = setup
    photos = [f"https://example.com/{n}.jpg" for n in range(5)]

    response = client.post("/api/tenant/maintenance", json={**REQUEST, "photo_urls": photos},
                           headers=auth_header(tenant))

    assert response.status_code == 400
    assert "photo_urls" in response.get_json()["fields"]


def test_only_our_cloudinary_photos_are_accepted_once_uploads_are_on(client, app, setup):
    app.config.update(CLOUDINARY_CLOUD_NAME="demo", CLOUDINARY_API_KEY="key", CLOUDINARY_API_SECRET="secret")
    _, tenant, _ = setup
    headers = auth_header(tenant)

    foreign = client.post("/api/tenant/maintenance", headers=headers,
                          json={**REQUEST, "photo_urls": ["https://example.com/x.jpg"]})
    ours = client.post("/api/tenant/maintenance", headers=headers,
                       json={**REQUEST, "photo_urls": ["https://res.cloudinary.com/demo/image/upload/x.jpg"]})

    assert foreign.status_code == 400
    assert ours.status_code == 201


def test_a_tenant_without_a_tenancy_cannot_report_an_issue(client, app):
    tenant = make_user("tenant")

    response = client.post("/api/tenant/maintenance", json=REQUEST, headers=auth_header(tenant))

    assert response.status_code == 400


def test_a_tenant_only_sees_their_own_requests(client, setup):
    _, tenant, tenancy = setup
    mine = make_request(tenancy)
    other = make_tenancy(make_user("tenant"), make_property(make_user("landlord"), name="Elsewhere"))
    theirs = make_request(other)
    headers = auth_header(tenant)

    listing = client.get("/api/tenant/maintenance", headers=headers).get_json()

    assert [r["id"] for r in listing] == [mine.id]
    assert client.get(f"/api/tenant/maintenance/{mine.id}", headers=headers).status_code == 200
    assert client.get(f"/api/tenant/maintenance/{theirs.id}", headers=headers).status_code == 404


# ----- landlord side -----
def test_a_landlord_sees_requests_for_their_properties(client, setup):
    landlord, _, tenancy = setup
    mine = make_request(tenancy)
    other = make_tenancy(make_user("tenant"), make_property(make_user("landlord"), name="Elsewhere"))
    make_request(other)

    listing = client.get("/api/landlord/maintenance", headers=auth_header(landlord)).get_json()

    assert [r["id"] for r in listing] == [mine.id]


def test_filter_requests_by_status(client, setup):
    landlord, _, tenancy = setup
    make_request(tenancy, status="pending")
    done = make_request(tenancy, status="resolved")

    listing = client.get("/api/landlord/maintenance?status=resolved", headers=auth_header(landlord)).get_json()

    assert [r["id"] for r in listing] == [done.id]


def test_a_landlord_can_update_the_status(client, setup):
    landlord, _, tenancy = setup
    row = make_request(tenancy)
    headers = auth_header(landlord)

    resolved = client.patch(f"/api/landlord/maintenance/{row.id}", json={"status": "resolved"}, headers=headers)

    assert resolved.status_code == 200
    db.session.refresh(row)
    assert row.status == "resolved"
    rejected = client.patch(f"/api/landlord/maintenance/{row.id}", json={"status": "rejected"}, headers=headers)
    assert rejected.get_json()["status"] == "rejected"


def test_an_invalid_status_is_refused(client, setup):
    landlord, _, tenancy = setup
    row = make_request(tenancy)

    response = client.patch(f"/api/landlord/maintenance/{row.id}", json={"status": "banana"},
                            headers=auth_header(landlord))

    assert response.status_code == 400


def test_another_landlord_cannot_touch_the_request(client, setup):
    _, _, tenancy = setup
    row = make_request(tenancy)
    stranger_headers = auth_header(make_user("landlord"))

    assert client.get(f"/api/landlord/maintenance/{row.id}", headers=stranger_headers).status_code == 404
    assert client.patch(f"/api/landlord/maintenance/{row.id}", json={"status": "resolved"},
                        headers=stranger_headers).status_code == 404


def test_a_tenant_cannot_change_a_status(client, setup):
    _, tenant, tenancy = setup
    row = make_request(tenancy)

    response = client.patch(f"/api/landlord/maintenance/{row.id}", json={"status": "resolved"},
                            headers=auth_header(tenant))

    assert response.status_code == 403
