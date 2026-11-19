import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def validate_database_url(database_url, *, allow_sqlite=False):
    if allow_sqlite and database_url and database_url.startswith("sqlite:"):
        return
    if not database_url:
        raise RuntimeError(
            "PostgreSQL is required. Configure DATABASE_URL with a PostgreSQL URL."
        )
    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError(
            "Only PostgreSQL is supported. Configure DATABASE_URL with a PostgreSQL URL."
        )


class Config:
    IS_VERCEL = os.getenv("VERCEL") == "1"
    DEFAULT_FRONTEND_URL = (
        "https://cribsy-system.vercel.app"
        if IS_VERCEL
        else "http://localhost:5173"
    )

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

    if IS_VERCEL:
        if not os.getenv("SECRET_KEY") or not os.getenv("JWT_SECRET_KEY"):
            raise RuntimeError(
                "SECRET_KEY and JWT_SECRET_KEY must be configured on Vercel."
            )

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRES_PRISMA_URL")
    )

    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", DEFAULT_FRONTEND_URL).split(",")
        if origin.strip()
    ]
    FRONTEND_URL = os.getenv("FRONTEND_URL", DEFAULT_FRONTEND_URL)

    # Development helper: also return verification codes / reset links in the response.
    # Set SHOW_DEV_CODES=false before deploying.
    SHOW_DEV_CODES = os.getenv(
        "SHOW_DEV_CODES",
        "false" if IS_VERCEL else "true"
    ).lower() == "true"

    if IS_VERCEL and SHOW_DEV_CODES:
        raise RuntimeError("SHOW_DEV_CODES must be false on Vercel.")

    # Cloudinary stores the uploaded images. Leave empty to turn uploads off (everything else still works).
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

    # SendGrid for sending emails
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")

    # Reject requests bigger than this (one image per request, each image at most 2 MB)
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024
