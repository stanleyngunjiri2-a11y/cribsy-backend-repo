"""OWNER: Member 4 (Nato). Landlord dashboard, own properties, tenants and tenancies."""
from flask import Blueprint, abort, jsonify, request

from ..extensions import db
from ..models import (
    ACTIVE_TENANCY, AVAILABILITY, PROPERTY_TYPES, TENANCY_STATUSES,
    Amenity, MaintenanceRequest, Property, RentPayment, Tenancy, User,
)
from ..uploads import is_valid_image_url
from ..utils import current_user, error, json_body, notify, parse_date, roles_required, to_int

bp = Blueprint("landlord", __name__)
URL_PREFIX = "/api/landlord"


# ---------- helpers ----------
def my_property_ids(user):
    return [p.id for p in Property.query.filter_by(landlord_id=user.id).all()]


def own_property_or_404(property_id, user):
    prop = db.get_or_404(Property, property_id)
    if prop.landlord_id != user.id:
        abort(404)  # do not reveal that someone else's property exists
    return prop


def own_tenancy_or_404(tenancy_id, user):
    tenancy = db.get_or_404(Tenancy, tenancy_id)
    if tenancy.property.landlord_id != user.id:
        abort(404)
    return tenancy


def validate_property(data):
    """Returns (clean_values, field_errors)."""
    fields, clean = {}, {}

    name = str(data.get("name") or "").strip()
    if len(name) < 3:
        fields["name"] = "Enter a property name (at least 3 characters)."
    clean["name"] = name

    location = str(data.get("location") or "").strip()
    if not location:
        fields["location"] = "Enter the location."
    clean["location"] = location

    property_type = data.get("property_type")
    if property_type not in PROPERTY_TYPES:
        fields["property_type"] = f"Choose one of: {', '.join(PROPERTY_TYPES)}."
    clean["property_type"] = property_type

    rent = to_int(data.get("monthly_rent"))
    if rent is None or rent <= 0:
        fields["monthly_rent"] = "Enter a monthly rent above 0."
    clean["monthly_rent"] = rent

    for key, label in (("bedrooms", "bedrooms"), ("bathrooms", "bathrooms")):
        value = to_int(data.get(key))
        if value is None or value < 0:
            fields[key] = f"Enter the number of {label}."
        clean[key] = value

    description = str(data.get("description") or "").strip()
    if len(description) < 10:
        fields["description"] = "Describe the property (at least 10 characters)."
    clean["description"] = description

    availability = data.get("availability", "vacant")
    if availability not in AVAILABILITY:
        fields["availability"] = "Must be vacant or occupied."
    clean["availability"] = availability

    image_url = str(data.get("image_url") or "").strip()
    if image_url and not is_valid_image_url(image_url):
        fields["image_url"] = "Upload the image first and use the link you get back."
    clean["image_url"] = image_url or None

    return clean, fields


def set_amenities(prop, names):
    prop.amenities = []
    for raw in names or []:
        name = str(raw).strip()
        if not name:
            continue
        amenity = Amenity.query.filter(db.func.lower(Amenity.name) == name.lower()).first()
        if amenity is None:
            amenity = Amenity(name=name)
            db.session.add(amenity)
        if amenity not in prop.amenities:
            prop.amenities.append(amenity)


# ---------- dashboard ----------
@bp.get("/dashboard")
@roles_required("landlord")
def dashboard():
    user = current_user()
    properties = Property.query.filter_by(landlord_id=user.id).all()
    ids = [p.id for p in properties]

    tenants = Tenancy.query.filter(
        Tenancy.property_id.in_(ids), Tenancy.status.in_(ACTIVE_TENANCY)
    ).count()
    pending = (
        MaintenanceRequest.query.join(Tenancy)
        .filter(Tenancy.property_id.in_(ids), MaintenanceRequest.status == "pending")
        .count()
    )
    recent = (
        RentPayment.query.join(Tenancy)
        .filter(Tenancy.property_id.in_(ids))
        .order_by(RentPayment.paid_on.desc(), RentPayment.id.desc())
        .limit(4)
        .all()
    )

    return jsonify({
        "total_properties": len(properties),
        "occupied_properties": sum(1 for p in properties if p.availability == "occupied"),
        "vacant_properties": sum(1 for p in properties if p.availability == "vacant"),
        "registered_tenants": tenants,
        "pending_maintenance": pending,
        "recent_payments": [r.to_dict() for r in recent],
    })


# ---------- properties ----------
@bp.get("/properties")
@roles_required("landlord")
def list_my_properties():
    props = Property.query.filter_by(landlord_id=current_user().id).order_by(Property.id).all()
    return jsonify([p.to_dict() for p in props])


@bp.post("/properties")
@roles_required("landlord")
def create_property():
    data = json_body()
    clean, fields = validate_property(data)
    if fields:
        return error("Please fix the highlighted fields.", 400, fields=fields)

    prop = Property(landlord_id=current_user().id, approval_status="pending", **clean)
    set_amenities(prop, data.get("amenities"))
    db.session.add(prop)
    db.session.commit()
    return jsonify(prop.to_dict()), 201  # stays "pending" until an admin approves it


@bp.get("/properties/<int:property_id>")
@roles_required("landlord")
def get_my_property(property_id):
    return jsonify(own_property_or_404(property_id, current_user()).to_dict())


@bp.put("/properties/<int:property_id>")
@roles_required("landlord")
def update_property(property_id):
    prop = own_property_or_404(property_id, current_user())
    data = json_body()
    clean, fields = validate_property(data)
    if fields:
        return error("Please fix the highlighted fields.", 400, fields=fields)

    for key, value in clean.items():
        setattr(prop, key, value)
    if "amenities" in data:
        set_amenities(prop, data["amenities"])
    db.session.commit()
    return jsonify(prop.to_dict())


@bp.delete("/properties/<int:property_id>")
@roles_required("landlord")
def delete_property(property_id):
    prop = own_property_or_404(property_id, current_user())
    if prop.tenancies:
        return error("This property has tenancy records and cannot be deleted.", 409)
    db.session.delete(prop)
    db.session.commit()
    return "", 204


# ---------- tenants and tenancies ----------
@bp.get("/tenants")
@roles_required("landlord")
def list_tenants():
    """Tenancies on this landlord's properties. Add ?include_ended=true to see past tenants too."""
    query = Tenancy.query.filter(Tenancy.property_id.in_(my_property_ids(current_user())))
    if request.args.get("include_ended") != "true":
        query = query.filter(Tenancy.status.in_(ACTIVE_TENANCY))
    return jsonify([t.to_dict() for t in query.order_by(Tenancy.id.desc()).all()])


@bp.post("/tenancies")
@roles_required("landlord")
def create_tenancy():
    """Assign a registered tenant to one of the landlord's vacant properties."""
    user = current_user()
    data = json_body()

    tenant_email = str(data.get("tenant_email") or "").strip().lower()
    property_id = to_int(data.get("property_id"))
    start = parse_date(data.get("start_date"))
    end = parse_date(data.get("end_date"))

    fields = {}
    if property_id is None:
        fields["property_id"] = "Choose a property."
    if start is None:
        fields["start_date"] = "Use the format YYYY-MM-DD."
    if end is None:
        fields["end_date"] = "Use the format YYYY-MM-DD."
    if start and end and end <= start:
        fields["end_date"] = "The end date must be after the start date."
    if not tenant_email:
        fields["tenant_email"] = "Enter the tenant's email."
    if fields:
        return error("Please fix the highlighted fields.", 400, fields=fields)

    prop = own_property_or_404(property_id, user)
    tenant = User.query.filter_by(email=tenant_email, role="tenant", status="active").first()
    if tenant is None:
        return error("No active tenant account was found with that email.", 404,
                     fields={"tenant_email": "Ask the tenant to register first."})
    if prop.approval_status != "approved":
        return error("Only approved properties can be assigned to a tenant.", 409)
    if prop.availability != "vacant":
        return error("This property is not vacant.", 409)
    if Tenancy.query.filter(Tenancy.tenant_id == tenant.id, Tenancy.status.in_(ACTIVE_TENANCY)).first():
        return error("This tenant already has an active tenancy.", 409)

    rent = to_int(data.get("monthly_rent")) or prop.monthly_rent
    tenancy = Tenancy(tenant_id=tenant.id, property_id=prop.id, start_date=start, end_date=end,
                      status="active", monthly_rent=rent)
    prop.availability = "occupied"
    db.session.add(tenancy)
    db.session.commit()

    notify(tenant, "You have been assigned a property",
           f"{prop.name} ({prop.location}) is now linked to your RentConnect account.")
    return jsonify(tenancy.to_dict()), 201


@bp.patch("/tenancies/<int:tenancy_id>")
@roles_required("landlord")
def update_tenancy(tenancy_id):
    tenancy = own_tenancy_or_404(tenancy_id, current_user())
    data = json_body()
    fields = {}

    if "status" in data:
        if data["status"] not in TENANCY_STATUSES:
            fields["status"] = f"Must be one of: {', '.join(TENANCY_STATUSES)}."
        else:
            tenancy.status = data["status"]
            tenancy.property.availability = "vacant" if tenancy.status == "ended" else "occupied"
    if "end_date" in data:
        end = parse_date(data["end_date"])
        if end is None or end <= tenancy.start_date:
            fields["end_date"] = "Use a date after the start date (YYYY-MM-DD)."
        else:
            tenancy.end_date = end

    if fields:
        db.session.rollback()
        return error("Please fix the highlighted fields.", 400, fields=fields)
    db.session.commit()
    return jsonify(tenancy.to_dict())