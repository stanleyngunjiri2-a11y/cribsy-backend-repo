from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from ..extensions import db
from ..models import Property, User

bp = Blueprint("properties", __name__)
URL_PREFIX = "/api"


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
