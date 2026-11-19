import pytest

from config import Config, validate_database_url


def test_postgresql_url_is_accepted():
    validate_database_url("postgresql+psycopg://user:password@localhost/cribsy")


def test_missing_database_url_is_rejected():
    with pytest.raises(RuntimeError, match="PostgreSQL is required"):
        validate_database_url(None)


def test_sqlite_url_is_rejected_outside_tests():
    with pytest.raises(RuntimeError, match="Only PostgreSQL is supported"):
        validate_database_url("sqlite:///cribsy.db")


def test_sqlite_url_is_allowed_for_tests():
    validate_database_url("sqlite://", allow_sqlite=True)


def test_database_engine_recycles_stale_connections():
    assert Config.SQLALCHEMY_ENGINE_OPTIONS == {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
