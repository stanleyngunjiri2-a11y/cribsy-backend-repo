from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import (
    Amenity,
    Enquiry,
    MaintenancePhoto,
    MaintenanceRequest,
    Property,
    RentPayment,
    Tenancy,
    User,
    db,
)


def seed_data():
    app = create_app()
    with app.app_context():
        db.create_all()

        if User.query.filter_by(email="landlord@example.com").first():
            print("Sample data already exists.")
            return

        landlord = User(
            full_name="Sample Landlord",
            email="landlord@example.com",
            phone="+1-555-0101",
            password_hash=generate_password_hash("ChangeMe123!"),
            role="landlord",
        )
        tenant = User(
            full_name="Sample Tenant",
            email="tenant@example.com",
            phone="+1-555-0102",
            password_hash=generate_password_hash("ChangeMe123!"),
            role="tenant",
        )
        amenities = [Amenity(name=name) for name in ("Laundry", "Parking", "Pet friendly")]
        rental = Property(
            landlord=landlord,
            title="Sunny two-bedroom apartment",
            description="A well-maintained apartment close to public transit.",
            address="125 Example Street",
            city="Springfield",
            state="IL",
            postal_code="62701",
            property_type="apartment",
            bedrooms=2,
            bathrooms=1.5,
            rent_amount=1450,
            is_available=False,
            amenities=amenities,
        )
        tenancy = Tenancy(
            property=rental,
            tenant=tenant,
            start_date=date.today() - timedelta(days=30),
            rent_amount=1450,
            status="active",
        )
        enquiry = Enquiry(
            property=rental,
            tenant=tenant,
            name=tenant.full_name,
            email=tenant.email,
            phone=tenant.phone,
            message="I would like to schedule a viewing.",
            status="new",
        )
        payment = RentPayment(
            tenancy=tenancy,
            amount=1450,
            due_date=date.today() + timedelta(days=1),
            status="pending",
            reference="SAMPLE-RENT-001",
        )
        request = MaintenanceRequest(
            tenancy=tenancy,
            title="Kitchen sink leak",
            description="Water is leaking from the pipe beneath the kitchen sink.",
            priority="normal",
            status="open",
        )
        photo = MaintenancePhoto(
            maintenance_request=request,
            photo_url="https://example.com/sample-maintenance-photo.jpg",
        )

        db.session.add_all(
            [landlord, tenant, *amenities, rental, tenancy, enquiry, payment, request, photo]
        )
        db.session.commit()
        print("Sample data created.")


if __name__ == "__main__":
    seed_data()
