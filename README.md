# RentConnect Backend

Flask REST API for a property-rental platform. It supports tenant and landlord accounts, landlord property management, tenancy assignment, rent payments, maintenance requests, image uploads, and administrator moderation.

## Features

- Registration and two-step sign-in with email verification codes
- Password-reset tokens
- JWT authentication with tenant, landlord, and admin roles
- Public property search and property details
- Landlord dashboards, properties, tenants, tenancies, and rent payments
- Tenant dashboards, tenancy details, rent history, and maintenance requests
- Maintenance status updates and optional maintenance photos
- Admin dashboards, user suspension, and property approval
- Cloudinary image uploads
- OpenAPI 3 specification

## Tech Stack

- Python
- Flask 3
- Flask-SQLAlchemy and SQLAlchemy
- Flask-Migrate / Alembic
- Flask-JWT-Extended
- Flask-CORS
- Flask-Bcrypt
- Cloudinary
- SQLite for local development; any SQLAlchemy-supported database can be configured

## Project Structure

```text
app/
  __init__.py          # Flask application factory
  extensions.py        # Database, JWT, CORS, and migration extensions
  model_registry.py    # SQLAlchemy models and shared enums
  routes/              # API blueprints
  uploads.py           # Cloudinary upload handling
  utils.py             # Authentication and shared validation helpers
api/index.py           # Vercel Python serverless entry point
docs/openapi.yaml      # OpenAPI 3 API specification
tests/                 # Pytest suite
migrations/            # Flask-Migrate configuration
app.py                 # WSGI entry point (runs on port 5555)
run.py                 # Development entry point (runs on port 5000)
seed.py                # Optional sample data
config.py              # Environment-backed configuration
vercel.json            # Vercel build and route configuration
```

The main application is the `app` package imported by `app.py` and `run.py`. The separate `server` package contains an older, partial implementation and is not the entry point used by these files.

## Requirements

- Python 3.10 or newer
- `pip`
- Optional: Cloudinary account for uploads
- Optional: a hosted PostgreSQL or other SQLAlchemy-compatible database

## Local Setup

```bash
git clone <repository-url>
cd cribsy-backend-repo

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-dev.txt
```

Create a `.env` file in the repository root. SQLite is the default, so no database variables are required for local development.

```dotenv
SECRET_KEY=change-this-in-production
JWT_SECRET_KEY=change-this-in-production
DATABASE_URL=sqlite:///cribsy.db
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
SHOW_DEV_CODES=true

# Optional image uploads
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Reserved for email integration
SENDGRID_API_KEY=
```

Initialize the database and load sample data:

```bash
python3 -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
python3 seed.py
```

The seed command is idempotent and does not duplicate data after the first run.

Start the server:

```bash
python3 app.py
```

This development entry point listens on `http://localhost:5555` with debug mode enabled.

Alternatively:

```bash
python3 run.py
```

This entry point listens on `http://localhost:5000`.

Check the server:

```bash
curl http://localhost:5555/api/health
```

Response:

```json
{"status":"ok","database":"ready"}
```

## Seed Accounts

| Role     | Email                       | Password      |
| -------- | --------------------------- | ------------- |
| Admin    | `admin@rentconnect.test`    | `Admin12345`  |
| Landlord | `landlord@rentconnect.test` | `Landlord123` |
| Tenant   | `jane@rentconnect.test`     | `Tenant1234`  |

The seed file also creates tenant accounts for `brian@rentconnect.test` and `mercy@rentconnect.test` with the tenant password.

## Authentication

1. Register as a tenant or landlord with `POST /api/auth/register`.
2. Sign in with `POST /api/auth/login`.
3. The API creates a six-digit verification code that expires after ten minutes.
4. In development, `SHOW_DEV_CODES=true` includes `dev_code` in the login response.
5. Exchange the code with `POST /api/auth/verify` to receive a JWT access token.
6. Send the token on protected routes:

```http
Authorization: Bearer <access_token>
```

Tokens expire after eight hours. Passwords must contain at least eight characters and include both letters and numbers.

Errors use the following shape:

```json
{ "error": "Something went wrong." }
```

Validation errors may include field-specific details:

```json
{
  "error": "Please fix the highlighted fields.",
  "fields": {
    "email": "Enter a valid email address."
  }
}
```

## Main API Routes

| Area              | Routes                                                                                                                                                           |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Health            | `GET /api/health`                                                                                                                                                |
| Authentication    | `/api/auth/register`, `/api/auth/login`, `/api/auth/verify`, `/api/auth/forgot-password`, `/api/auth/reset-password`, `/api/auth/me`                             |
| Public properties | `GET /api/meta`, `GET /api/properties`, `GET /api/properties/<property_id>`, `POST /api/properties/<property_id>/enquiries` |
| Uploads           | `POST /api/uploads/image`                                                                                                                                        |
| Landlord          | `/api/landlord/dashboard`, `/api/landlord/properties`, `/api/landlord/tenants`, `/api/landlord/tenancies`, `/api/landlord/payments`, `/api/landlord/maintenance` |
| Tenant            | `/api/tenant/dashboard`, `/api/tenant/tenancy`, `/api/tenant/payments`, `/api/tenant/maintenance`                                                                |
| Admin             | `/api/admin/stats`, `/api/admin/users`, `/api/admin/properties`                                                                                                  |

The complete request and response specification is in [docs/openapi.yaml](docs/openapi.yaml).

## API Documentation

The interactive Swagger UI is served at [`http://localhost:5555/api/docs`](http://localhost:5555/api/docs), and the OpenAPI specification is served at [`http://localhost:5555/api/openapi.yaml`](http://localhost:5555/api/openapi.yaml). The source specification is [docs/openapi.yaml](docs/openapi.yaml).

## Database Migrations

Flask-Migrate is initialized in the application and migration configuration is in `migrations/`. The repository currently has no migration revisions in `migrations/versions`, so `db.create_all()` is the documented local setup method.

For a future migration workflow:

```bash
flask --app app.py db migrate -m "Describe the change"
flask --app app.py db upgrade
```

## Image Uploads

Landlords and tenants can upload one JPG, PNG, or WebP image at:

```http
POST /api/uploads/image
Content-Type: multipart/form-data
```

Use the multipart field name `file`. The maximum size is 2 MB. Set all three Cloudinary environment variables before uploading.

The returned `url` can be:

- Assigned to a property's `image_url`
- Submitted in a maintenance request's `photo_urls`

When Cloudinary is not configured, property and maintenance APIs still work, but image upload requests return `503`.

## Email Behavior

Email content is currently written to the Flask application log. `SENDGRID_API_KEY` is reserved in configuration but the active implementation has not yet integrated SendGrid or another email provider.

Set `SHOW_DEV_CODES=false` in production. The development setting exposes verification codes and password-reset links in API responses.

## Configuration

| Variable                | Default                    | Purpose                                                |
| ----------------------- | -------------------------- | ------------------------------------------------------ |
| `SECRET_KEY`            | `dev-secret-change-me`     | Password-reset token signing                           |
| `JWT_SECRET_KEY`        | `dev-jwt-secret-change-me` | JWT signing                                            |
| `DATABASE_URL`          | `sqlite:///cribsy.db`      | SQLAlchemy database URL                                |
| `CORS_ORIGINS`          | `http://localhost:5173`    | Comma-separated allowed origins                        |
| `FRONTEND_URL`          | `http://localhost:5173`    | Password-reset frontend base URL                       |
| `SHOW_DEV_CODES`        | `true`                     | Include development codes and reset links in responses |
| `CLOUDINARY_CLOUD_NAME` | Empty                      | Cloudinary cloud name                                  |
| `CLOUDINARY_API_KEY`    | Empty                      | Cloudinary API key                                     |
| `CLOUDINARY_API_SECRET` | Empty                      | Cloudinary API secret                                  |
| `SENDGRID_API_KEY`      | Empty                      | Reserved for future email delivery                     |

## Deploy to Vercel

The repository includes `api/index.py` and `vercel.json`. Vercel serves the Flask application as a Python serverless function.

### 1. Create a persistent database

Do not use the default SQLite database in production. SQLite data is ephemeral in serverless deployments.

Create a PostgreSQL database or use a Vercel Postgres/Neon integration, then set the database URL in Vercel:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Vercel database integrations that expose `POSTGRES_URL` or `POSTGRES_PRISMA_URL` are also detected automatically.

### 2. Configure environment variables

Add these variables in the Vercel project settings:

| Variable | Required | Example |
|---|---|---|
| `DATABASE_URL` | Yes | `postgresql://...` |
| `SECRET_KEY` | Yes | A strong random string |
| `JWT_SECRET_KEY` | Yes | A different strong random string |
| `CORS_ORIGINS` | Yes | `https://your-frontend.vercel.app` |
| `FRONTEND_URL` | Yes | `https://your-frontend.vercel.app` |
| `SHOW_DEV_CODES` | Yes | `false` |
| `CLOUDINARY_CLOUD_NAME` | For uploads | Your Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | For uploads | Your Cloudinary API key |
| `CLOUDINARY_API_SECRET` | For uploads | Your Cloudinary API secret |

`CORS_ORIGINS` accepts comma-separated origins:

```text
CORS_ORIGINS=https://app.example.com,https://www.app.example.com
```

### 3. Initialize the database

Run schema creation against the hosted database from a local environment:

```bash
DATABASE_URL="postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require" \
python3 -c "from app import create_app; from app.extensions import db; app=create_app(); app.app_context().push(); db.create_all()"
```

Optionally seed the database:

```bash
DATABASE_URL="postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require" python3 seed.py
```

The repository currently has no migration revision files. Create and maintain Alembic migrations before using the API for production schema changes.

### 4. Deploy

Import the Git repository in Vercel or run:

```bash
vercel
```

Use `vercel --prod` for a production deployment.

After deployment, verify:

```text
https://YOUR-PROJECT.vercel.app/api/health
https://YOUR-PROJECT.vercel.app/api/docs
https://YOUR-PROJECT.vercel.app/api/openapi.yaml
```

## Testing

Install the development requirements, then run:

```bash
python3 -m pytest
```

Run a specific test file:

```bash
python3 -m pytest tests/test_auth.py
```

Tests use a fresh in-memory SQLite database and do not write to `cribsy.db`.

## Production Notes

- Replace both development secret keys with strong, separate random values.
- Set `SHOW_DEV_CODES=false`.
- Use a managed database and set `DATABASE_URL`.
- Restrict `CORS_ORIGINS` to the deployed frontend origin.
- Configure Cloudinary credentials if uploads are required.
- Integrate an email provider before relying on verification codes or password resets.
- Use a production WSGI server instead of Flask's development server.

Example WSGI entry points:

```text
app:app
app:application
run:app
```
