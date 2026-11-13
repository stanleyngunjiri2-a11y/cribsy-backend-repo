"""OWNER: Member 1 (Stanley). Image uploads. Cloudinary itself is replaced by a fake, so no internet is needed."""
import io

import pytest

from app.uploads import is_valid_image_url
from tests.helpers import auth_header, make_user


def photo(name="photo.jpg", content_type="image/jpeg"):
    return {"file": (io.BytesIO(b"fake image bytes"), name, content_type)}


def turn_on_cloudinary(app):
    app.config.update(CLOUDINARY_CLOUD_NAME="demo", CLOUDINARY_API_KEY="key", CLOUDINARY_API_SECRET="secret")


def test_upload_needs_sign_in(client):
    response = client.post("/api/uploads/image", data=photo(), content_type="multipart/form-data")

    assert response.status_code == 401


def test_admin_cannot_upload(client):
    admin = make_user("admin")
    response = client.post("/api/uploads/image", data=photo(), content_type="multipart/form-data",
                           headers=auth_header(admin))

    assert response.status_code == 403


def test_upload_without_a_file_is_rejected(client):
    landlord = make_user("landlord")
    response = client.post("/api/uploads/image", data={}, content_type="multipart/form-data",
                           headers=auth_header(landlord))

    assert response.status_code == 400


def test_upload_says_so_when_cloudinary_is_not_set_up(client):
    landlord = make_user("landlord")
    response = client.post("/api/uploads/image", data=photo(), content_type="multipart/form-data",
                           headers=auth_header(landlord))

    assert response.status_code == 503


def test_upload_returns_the_link(client, app, monkeypatch):
    turn_on_cloudinary(app)
    folders = []

    def fake_upload(file, folder):
        folders.append(folder)
        return {"url": "https://res.cloudinary.com/demo/image/upload/a.jpg", "public_id": "a"}

    monkeypatch.setattr("app.routes.uploads.upload_image", fake_upload)
    landlord = make_user("landlord")
    tenant = make_user("tenant")

    first = client.post("/api/uploads/image", data=photo(), content_type="multipart/form-data",
                        headers=auth_header(landlord))
    second = client.post("/api/uploads/image", data=photo(), content_type="multipart/form-data",
                         headers=auth_header(tenant))

    assert first.status_code == 201
    assert first.get_json()["url"].startswith("https://res.cloudinary.com/demo/")
    assert folders == ["properties", "maintenance"]  # landlords and tenants use different folders
    assert second.status_code == 201


def test_upload_rejects_a_file_that_is_not_an_image(client, app):
    pytest.importorskip("cloudinary")
    turn_on_cloudinary(app)
    landlord = make_user("landlord")

    response = client.post("/api/uploads/image", data=photo("notes.txt", "text/plain"),
                           content_type="multipart/form-data", headers=auth_header(landlord))

    assert response.status_code == 400
    assert "image" in response.get_json()["error"].lower()


def test_without_cloudinary_any_https_link_is_accepted(app):
    assert is_valid_image_url("https://example.com/a.jpg")
    assert not is_valid_image_url("http://example.com/a.jpg")
    assert not is_valid_image_url(None)


def test_with_cloudinary_only_our_links_are_accepted(app):
    turn_on_cloudinary(app)

    assert is_valid_image_url("https://res.cloudinary.com/demo/image/upload/a.jpg")
    assert not is_valid_image_url("https://res.cloudinary.com/someone-else/image/upload/a.jpg")
    assert not is_valid_image_url("https://example.com/a.jpg")
