"""OWNER: Member 3 (Quincy). Public property search, filters, pagination and details."""
from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models import (
    MAINTENANCE_CATEGORIES,
    MAINTENANCE_STATUSES,
    PAYMENT_METHODS,
    PROPERTY_TYPES,
    Amenity,
    Enquiry,
    Property,
    User,
)
from ..utils import error, is_email, json_body, notify

bp = Blueprint("properties", __name__)
URL_PREFIX = "/api"


@bp.get("/meta")
def meta():
    """Dropdown values used by the frontend."""
    return jsonify({
        "property_types": list(PROPERTY_TYPES),
        "maintenance_categories": list(MAINTENANCE_CATEGORIES),
        "maintenance_statuses": list(MAINTENANCE_STATUSES),
        "payment_methods": list(PAYMENT_METHODS),
        "amenities": [a.name for a in Amenity.query.order_by(Amenity.name).all()],
    })


@bp.get("/properties")
def list_properties():
    """Search + filters + pagination. Only approved properties are public."""
    args = request.args
    query = Property.query.filter(Property.approval_status == "approved")

    location = args.get("location", "").strip()
    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))

    min_rent = args.get("min_rent", type=int)
    max_rent = args.get("max_rent", type=int)
    if min_rent is not None:
        query = query.filter(Property.monthly_rent >= min_rent)
    if max_rent is not None:
        query = query.filter(Property.monthly_rent <= max_rent)

    property_type = args.get("type", "").strip()
    if property_type:
        query = query.filter(Property.property_type == property_type)

    bedrooms = args.get("bedrooms", type=int)
    if bedrooms:
        # "4" means "4 or more", matching the frontend filter
        query = query.filter(Property.bedrooms >= 4 if bedrooms >= 4 else Property.bedrooms == bedrooms)

    availability = args.get("availability")
    if availability == "available":
        query = query.filter(Property.availability == "vacant")
    elif availability == "unavailable":
        query = query.filter(Property.availability == "occupied")

    page = max(args.get("page", 1, type=int), 1)
    per_page = min(max(args.get("per_page", 6, type=int), 1), 24)
    result = query.order_by(Property.id).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "items": [p.to_dict() for p in result.items],
        "page": result.page,
        "per_page": per_page,
        "total": result.total,
        "pages": result.pages or 1,
    })


@bp.get("/properties/<int:property_id>")
def property_detail(property_id):
    prop = db.get_or_404(Property, property_id)

    if prop.approval_status != "approved":
        # Not public yet: only the owner or an admin may look at it.
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        user = db.session.get(User, int(identity)) if identity else None
        if user is None or (user.role != "admin" and prop.landlord_id != user.id):
            abort(404)

    return jsonify(prop.to_dict(include_landlord=True))


@bp.post("/properties/<int:property_id>/enquiries")
def create_enquiry(property_id):
    prop = db.get_or_404(Property, property_id)
    if prop.approval_status != "approved":
        abort(404)

    data = json_body()
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    message = str(data.get("message") or "").strip()

    fields = {}
    if len(name) < 2:
        fields["name"] = "Enter your name."
    if not is_email(email):
        fields["email"] = "Enter a valid email address."
    if len(message) < 10:
        fields["message"] = "Describe your enquiry in at least 10 characters."
    if fields:
        return error("Please fix the highlighted fields.", 400, fields=fields)

    enquiry = Enquiry(property_id=prop.id, name=name, email=email, message=message)
    db.session.add(enquiry)
    db.session.commit()

    notify(
        prop.landlord,
        f"New enquiry about {prop.name}",
        f"{name} ({email}) sent this enquiry:\n\n{message}",
    )
    return jsonify(enquiry.to_dict()), 201
