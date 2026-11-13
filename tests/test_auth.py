"""OWNER: Member 1 (Stanley). Register, two-step sign-in, password reset and profile."""
from app.models import User
from tests.helpers import PASSWORD, auth_header, make_user

VALID = {"full_name": "Jane Wanjiku", "email": "jane@test.com", "phone": "0712345678",
         "role": "tenant", "password": "Passw0rd1"}


def test_register_creates_an_account(client):
    response = client.post("/api/auth/register", json=VALID)

    assert response.status_code == 201
    body = response.get_json()
    assert body["email"] == "jane@test.com"
    assert "password" not in body and "password_hash" not in body
    assert User.query.filter_by(email="jane@test.com").count() == 1


def test_register_rejects_a_duplicate_email(client):
    client.post("/api/auth/register", json=VALID)
    response = client.post("/api/auth/register", json=VALID)

    assert response.status_code == 409


def test_register_cannot_create_an_admin(client):
    response = client.post("/api/auth/register", json={**VALID, "role": "admin"})

    assert response.status_code == 400
    assert "role" in response.get_json()["fields"]


def test_register_reports_every_invalid_field(client):
    response = client.post("/api/auth/register", json={})

    assert response.status_code == 400
    assert {"full_name", "email", "phone", "role", "password"} <= set(response.get_json()["fields"])


def test_login_with_a_wrong_password_fails(client):
    user = make_user()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "WrongPass1"})

    assert response.status_code == 401


def test_login_then_verify_gives_a_working_token(client):
    user = make_user()

    login = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert login.status_code == 200
    assert login.get_json()["verification_required"] is True
    code = login.get_json()["dev_code"]

    verify = client.post("/api/auth/verify", json={"email": user.email, "code": code})
    assert verify.status_code == 200
    token = verify.get_json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.get_json()["email"] == user.email


def test_verify_rejects_a_wrong_code(client):
    user = make_user()
    code = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).get_json()["dev_code"]
    wrong = "000000" if code != "000000" else "111111"

    response = client.post("/api/auth/verify", json={"email": user.email, "code": wrong})

    assert response.status_code == 400


def test_a_code_works_only_once(client):
    user = make_user()
    code = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD}).get_json()["dev_code"]

    first = client.post("/api/auth/verify", json={"email": user.email, "code": code})
    second = client.post("/api/auth/verify", json={"email": user.email, "code": code})

    assert first.status_code == 200
    assert second.status_code == 400


def test_a_suspended_user_cannot_log_in(client):
    user = make_user(status="suspended")
    response = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})

    assert response.status_code == 403


def test_protected_routes_need_a_token(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "error" in response.get_json()


def test_forgot_password_does_not_reveal_which_emails_exist(client):
    user = make_user()

    known = client.post("/api/auth/forgot-password", json={"email": user.email})
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@test.com"})

    assert known.status_code == unknown.status_code == 200
    assert known.get_json()["message"] == unknown.get_json()["message"]
    assert "dev_reset_link" in known.get_json()
    assert "dev_reset_link" not in unknown.get_json()


def test_reset_password_changes_the_password_once(client):
    user = make_user()
    link = client.post("/api/auth/forgot-password", json={"email": user.email}).get_json()["dev_reset_link"]
    token = link.split("token=")[1]

    reset = client.post("/api/auth/reset-password", json={"token": token, "password": "NewPass123"})
    assert reset.status_code == 200

    old = client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    new = client.post("/api/auth/login", json={"email": user.email, "password": "NewPass123"})
    assert old.status_code == 401
    assert new.status_code == 200

    again = client.post("/api/auth/reset-password", json={"token": token, "password": "Another123"})
    assert again.status_code == 400


def test_reset_password_rejects_a_bad_token(client):
    response = client.post("/api/auth/reset-password", json={"token": "not-a-token", "password": "NewPass123"})

    assert response.status_code == 400


def test_update_profile(client):
    user = make_user()
    response = client.patch("/api/auth/me", json={"full_name": "New Name", "email_notifications": False},
                            headers=auth_header(user))

    assert response.status_code == 200
    assert response.get_json()["full_name"] == "New Name"
    assert response.get_json()["email_notifications"] is False


def test_update_profile_rejects_an_email_already_in_use(client):
    first = make_user()
    second = make_user()
    response = client.patch("/api/auth/me", json={"email": first.email}, headers=auth_header(second))

    assert response.status_code == 400
    assert "email" in response.get_json()["fields"]
