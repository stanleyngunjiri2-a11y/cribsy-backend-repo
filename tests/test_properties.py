import pytest

from tests.helpers import auth_header, make_property, make_user


@pytest.fixture()
def landlord(app):
    return make_user("landlord")


def names(response):
    return [p["name"] for p in response.get_json()["items"]]


def test_only_approved_properties_are_listed(client, landlord):
    make_property(landlord, name="Approved")
    make_property(landlord, name="Waiting", approval_status="pending")
    make_property(landlord, name="Turned down", approval_status="rejected")

    assert names(client.get("/api/properties")) == ["Approved"]


def test_filter_by_location_ignores_case(client, landlord):
    make_property(landlord, name="Ruiru one", location="Ruiru, Kiambu")
    make_property(landlord, name="Nyali one", location="Nyali, Mombasa")

    assert names(client.get("/api/properties?location=ruiru")) == ["Ruiru one"]


def test_filter_by_rent_range(client, landlord):
    make_property(landlord, name="Cheap", monthly_rent=10000)
    make_property(landlord, name="Middle", monthly_rent=30000)
    make_property(landlord, name="Pricey", monthly_rent=60000)

    assert names(client.get("/api/properties?min_rent=20000&max_rent=40000")) == ["Middle"]
    assert names(client.get("/api/properties?max_rent=10000")) == ["Cheap"]
    assert names(client.get("/api/properties?min_rent=60000")) == ["Pricey"]


def test_filter_by_property_type(client, landlord):
    make_property(landlord, name="A flat", property_type="Apartment")
    make_property(landlord, name="A house", property_type="House")

    assert names(client.get("/api/properties?type=House")) == ["A house"]


def test_filter_by_bedrooms_where_four_means_four_or_more(client, landlord):
    for number in (1, 2, 4, 5):
        make_property(landlord, name=f"{number} bed", bedrooms=number)

    assert names(client.get("/api/properties?bedrooms=2")) == ["2 bed"]
    assert names(client.get("/api/properties?bedrooms=4")) == ["4 bed", "5 bed"]


def test_filter_by_availability(client, landlord):
    make_property(landlord, name="Free", availability="vacant")
    make_property(landlord, name="Taken", availability="occupied")

    assert names(client.get("/api/properties?availability=available")) == ["Free"]
    assert names(client.get("/api/properties?availability=unavailable")) == ["Taken"]


def test_pagination(client, landlord):
    for number in range(5):
        make_property(landlord, name=f"Home {number}")

    first = client.get("/api/properties?per_page=2&page=1").get_json()
    last = client.get("/api/properties?per_page=2&page=3").get_json()

    assert first["total"] == 5
    assert first["pages"] == 3
    assert len(first["items"]) == 2
    assert len(last["items"]) == 1


def test_property_details_are_public(client, landlord):
    prop = make_property(landlord, name="Open house")

    response = client.get(f"/api/properties/{prop.id}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["name"] == "Open house"
    assert body["landlord"]["full_name"] == landlord.full_name
    assert "email" not in body["landlord"]  # the landlord's contact details stay private


def test_an_unknown_property_is_404(client):
    assert client.get("/api/properties/999").status_code == 404


def test_an_unapproved_property_is_hidden_from_the_public(client, landlord):
    prop = make_property(landlord, approval_status="pending")

    assert client.get(f"/api/properties/{prop.id}").status_code == 404


def test_the_owner_and_an_admin_can_see_an_unapproved_property(client, landlord):
    prop = make_property(landlord, approval_status="pending")
    admin = make_user("admin")
    other_landlord = make_user("landlord")

    assert client.get(f"/api/properties/{prop.id}", headers=auth_header(landlord)).status_code == 200
    assert client.get(f"/api/properties/{prop.id}", headers=auth_header(admin)).status_code == 200
    assert client.get(f"/api/properties/{prop.id}", headers=auth_header(other_landlord)).status_code == 404
