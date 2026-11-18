"""OWNER: Member 1 (Stanley). Gives every test a fresh, empty in-memory database and a test client."""
import pytest

from app import create_app
from app.extensions import db
from config import Config


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # in memory: nothing is written to disk
    SECRET_KEY = "test-secret-key"
    JWT_SECRET_KEY = "test-jwt-secret-key-that-is-long-enough"
    SHOW_DEV_CODES = True  # login and forgot-password return the code / link, so tests can use them
    CLOUDINARY_CLOUD_NAME = ""
    CLOUDINARY_API_KEY = ""
    CLOUDINARY_API_SECRET = ""


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
