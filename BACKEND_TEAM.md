# Backend: who builds what

Every member owns separate files, so nobody edits the same file. Each model file and route file starts
with an `OWNER:` line. Models and routes are picked up automatically, so no shared file needs editing.

| Member | Name | Models | Routes | Other |
|---|---|---|---|---|
| 1 | Stanley | `models/user.py`, `models/common.py` | `routes/auth.py`, `routes/uploads.py` (Cloudinary image upload) | Project base: `config.py`, `app/__init__.py`, `extensions.py`, `utils.py`, `uploads.py`, `create_db.py`, migrations, README |
| 2 | Alex | `models/enquiry.py` | `routes/enquiries.py` (dropdown values + enquiries) | `seed.py` (sample data) |
| 3 | Quincy | `models/property.py` (Property, Amenity) | `routes/properties.py` (search, filters, pagination, details) | |
| 4 | Nato | `models/tenancy.py` | `routes/landlord.py` (dashboard, my properties, tenants, assign a tenant) | |
| 5 | Sam | `models/payment.py` | `routes/landlord_payments.py`, `routes/tenant.py` (dashboard, rent history) | |
| 6 | Lynn | `models/maintenance.py` | `routes/maintenance.py`, `routes/admin.py` | |

## Order to push

1. **Member 1 first:** the project base, users and sign-in. Push to `develop`. Everyone pulls it.
2. **Models next, in this order** (a model only refers to models above it): Quincy's `property.py`, then
   Nato's `tenancy.py`, then Alex's `enquiry.py`, Sam's `payment.py`, Lynn's `maintenance.py`.
   Each person pulls `develop`, adds their model file, runs `python create_db.py` to check it, and opens a pull request.
3. **Routes after all models are merged.** Your routes import other people's models, so pull `develop` first.
4. **Member 1** generates the migration once everything is merged: `flask db init`, `flask db migrate`, `flask db upgrade`, and pushes `migrations/`.
5. **Member 2** runs `seed.py` last and checks the sample data loads.

## Rules

- Branch from `develop`: `feature/backend-member-N-name`. Only edit your own files.
- A broken file stops the whole app from starting, so run `flask run` and open `/api/health` before every pull request.
- Test your routes with the sample accounts in `README.md` and a tool like Postman or curl.
- If you need a change in someone else's file, ask the owner.

## Image uploads

Images go to Cloudinary through `POST /api/uploads/image` (Stanley). Nato (`image_url`) and Lynn (`photo_urls`) only check that a saved link is one of ours. Setup steps are in `README.md`.

## Tests

Run `pipenv install -r requirements-dev.txt`, then `pytest`. Each member writes and fixes the tests for their own files:

| Member | Test files |
|---|---|
| 1, Stanley | `tests/conftest.py`, `tests/helpers.py`, `tests/test_auth.py`, `tests/test_uploads.py` |
| 2, Alex | `tests/test_enquiries.py`, `tests/test_seed.py` |
| 3, Quincy | `tests/test_properties.py` |
| 4, Nato | `tests/test_landlord.py` |
| 5, Sam | `tests/test_payments.py` |
| 6, Lynn | `tests/test_maintenance.py`, `tests/test_admin.py` |

Stanley pushes `conftest.py`, `helpers.py`, `pytest.ini` and `requirements-dev.txt` first, because every test file uses them.
Run your own test file before every pull request. If a test fails, either the code or the test is wrong, so read the message and fix the right one.
