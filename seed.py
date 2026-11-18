
from datetime import date

from app import create_app
from app.extensions import db
from app.models import (
    Amenity, MaintenancePhoto, MaintenanceRequest, Property, RentPayment, Tenancy, User,
)

PASSWORDS = {"admin": "Admin12345", "landlord": "Landlord123", "tenant": "Tenant1234"}

PROPERTIES = [
    # name, location, type, rent, beds, baths, amenities, description
    ("Greenview Apartments", "Ruiru, Kiambu", "Apartment", 28000, 2, 1, ["Water supply", "Parking", "Security"],
     "A bright two-bedroom apartment close to shops and the main road."),
    ("Oak Residence", "Kasarani, Nairobi", "Apartment", 35000, 2, 2, ["Balcony", "Water supply", "Security"],
     "A modern apartment with a balcony and a secure compound."),
    ("Sunrise Family Home", "Kahawa Sukari, Kiambu", "House", 52000, 3, 2, ["Parking", "Garden", "Water supply"],
     "A spacious family home with a small garden."),
    ("Maple Court Studio", "Westlands, Nairobi", "Studio", 22000, 1, 1, ["Security", "Water supply"],
     "A compact studio suited to a single professional."),
    ("Lakeview Bedsitter", "Kisumu Central, Kisumu", "Bedsitter", 9000, 1, 1, ["Water supply"],
     "An affordable bedsitter near the town centre."),
    ("Palm Grove Maisonette", "Nyali, Mombasa", "House", 65000, 4, 3, ["Parking", "Garden", "Security", "Water supply"],
     "A four-bedroom maisonette in a quiet neighbourhood."),
    ("Hillside Apartments", "Thika Road, Nairobi", "Apartment", 30000, 2, 2, ["Parking", "Security"],
     "A two-bedroom unit with good access to public transport."),
    ("Acacia Single Room", "Juja, Kiambu", "Bedsitter", 7000, 1, 1, ["Water supply"],
     "A simple room popular with students."),
    ("Riverside Townhouse", "Ruaka, Kiambu", "House", 48000, 3, 3, ["Parking", "Security", "Garden"],
     "A three-bedroom townhouse in a gated community."),
    ("Skyline Studio", "Kilimani, Nairobi", "Studio", 38000, 1, 1, ["Lift", "Security", "Backup power"],
     "A modern studio with a lift and backup power."),
]
PENDING = {"Maple Court Studio", "Lakeview Bedsitter"}  # waiting for admin approval


def make_user(full_name, email, phone, role, password):
    user = User(full_name=full_name, email=email, phone=phone, role=role)
    user.set_password(password)
    db.session.add(user)
    return user


def seed(app=None):
    app = app or create_app()
    with app.app_context():
        if User.query.first():
            print("The database already has users. Nothing to do.")
            return

        make_user("Site Admin", "admin@rentconnect.test", "0700 000 000", "admin", PASSWORDS["admin"])
        landlord = make_user("Sample Landlord", "landlord@rentconnect.test", "0700 111 111", "landlord",
                             PASSWORDS["landlord"])
        jane = make_user("Jane Wanjiku", "jane@rentconnect.test", "0712 345 678", "tenant", PASSWORDS["tenant"])
        brian = make_user("Brian Otieno", "brian@rentconnect.test", "0723 456 789", "tenant", PASSWORDS["tenant"])
        mercy = make_user("Mercy Chebet", "mercy@rentconnect.test", "0734 567 890", "tenant", PASSWORDS["tenant"])
        db.session.flush()  # gives every user an id

        amenities = {}
        properties = []
        for name, location, kind, rent, beds, baths, amenity_names, description in PROPERTIES:
            prop = Property(landlord_id=landlord.id, name=name, location=location, property_type=kind,
                            monthly_rent=rent, bedrooms=beds, bathrooms=baths, description=description,
                            approval_status="pending" if name in PENDING else "approved")
            for amenity_name in amenity_names:
                if amenity_name not in amenities:
                    amenities[amenity_name] = Amenity(name=amenity_name)
                prop.amenities.append(amenities[amenity_name])
            db.session.add(prop)
            properties.append(prop)
        db.session.flush()

        greenview, oak, sunrise = properties[0], properties[1], properties[2]
        tenancies = [
            Tenancy(tenant_id=jane.id, property_id=greenview.id, start_date=date(2026, 2, 1),
                    end_date=date(2027, 1, 31), status="active", monthly_rent=greenview.monthly_rent),
            Tenancy(tenant_id=brian.id, property_id=oak.id, start_date=date(2026, 5, 1),
                    end_date=date(2027, 4, 30), status="active", monthly_rent=oak.monthly_rent),
            Tenancy(tenant_id=mercy.id, property_id=sunrise.id, start_date=date(2025, 11, 1),
                    end_date=date(2026, 10, 31), status="notice", monthly_rent=sunrise.monthly_rent),
        ]
        for prop in (greenview, oak, sunrise):
            prop.availability = "occupied"
        db.session.add_all(tenancies)
        db.session.flush()

        jane_tenancy = tenancies[0]
        history = [  # paid_on, status, method
            (date(2026, 11, 2), "paid", "Mobile money"), (date(2026, 10, 2), "paid", "Mobile money"),
            (date(2026, 9, 3), "paid", "Bank transfer"), (date(2026, 8, 2), "paid", "Mobile money"),
            (date(2026, 7, 10), "pending", "Bank transfer"), (date(2026, 6, 2), "overdue", "Mobile money"),
        ]
        for number, (paid_on, status, method) in enumerate(history, start=1):
            db.session.add(RentPayment(tenancy_id=jane_tenancy.id, amount=greenview.monthly_rent, paid_on=paid_on,
                                       reference=f"SAMPLE-{1000 + number}", method=method, status=status))
        db.session.add(RentPayment(tenancy_id=tenancies[1].id, amount=oak.monthly_rent, paid_on=date(2026, 11, 3),
                                   reference="SAMPLE-2001", method="Mobile money", status="paid"))

        leak = MaintenanceRequest(tenancy_id=jane_tenancy.id, category="Plumbing", status="in_progress",
                                  description="The kitchen tap has been leaking for three days.")
        leak.photos.append(MaintenancePhoto(file_url="https://example.com/sample-photo-1.jpg"))
        db.session.add_all([
            leak,
            MaintenanceRequest(tenancy_id=jane_tenancy.id, category="Electrical", status="resolved",
                               description="The hallway light does not switch on."),
            MaintenanceRequest(tenancy_id=tenancies[1].id, category="Doors and locks", status="pending",
                               description="The balcony door lock is broken and the door cannot be secured."),
        ])

        db.session.commit()
        print("Sample data added.\n")
        print("Sign in with (password in brackets):")
        print(f"  admin@rentconnect.test     [{PASSWORDS['admin']}]")
        print(f"  landlord@rentconnect.test  [{PASSWORDS['landlord']}]")
        print(f"  jane@rentconnect.test      [{PASSWORDS['tenant']}]  (also brian@ and mercy@)")


if __name__ == "__main__":
    seed()
