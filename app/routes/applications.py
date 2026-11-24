"""Tenant applications, landlord reviews, property units and assignments."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    ACTIVE_TENANCY,
    Property,
    PropertyApplication,
    PropertyUnit,
    Tenancy,
    User,
    utcnow,
)
from ..utils import (
    current_user,
    error,
    json_body,
    notify,
    parse_date,
    roles_required,
    to_int,
)

bp = Blueprint("applications", __name__)
URL_PREFIX = "/api"


def update_property_availability(prop):
    """A multi-unit property is vacant while at least one unit is available."""
    if prop.units:
        occupied = sum(
            1 for unit in prop.units
            if any(t.status in ACTIVE_TENANCY for t in unit.tenancies)
        )
        prop.availability = "occupied" if occupied >= len(prop.units) else "vacant"
    else:
        active = any(t.status in ACTIVE_TENANCY for t in prop.tenancies)
        prop.availability = "occupied" if active else "vacant"


def landlord_property_or_404(property_id, landlord):
    prop = Property.query.filter_by(
        id=property_id, landlord_id=landlord.id
    ).first()
    return prop


# ---------------- TENANT APPLICATIONS ----------------

@bp.post("/properties/<int:property_id>/applications")
@roles_required("tenant")
def submit_application(property_id):
    tenant = current_user()
    data = json_body()

    prop = db.session.get(Property, property_id)
    if prop is None or prop.approval_status != "approved":
        return error("This property is not currently accepting applications.", 404)

    if Tenancy.query.filter(
        Tenancy.tenant_id == tenant.id,
        Tenancy.status.in_(ACTIVE_TENANCY),
    ).first():
        return error("You already have an active tenancy. End it before applying for another property.", 409)

    if prop.availability != "vacant":
        return error("This property is currently marked as occupied.", 409)

    existing = PropertyApplication.query.filter(
        PropertyApplication.property_id == prop.id,
        PropertyApplication.tenant_id == tenant.id,
        PropertyApplication.status.in_(("pending", "approved")),
    ).first()

    if existing:
        return error("You already have a pending or approved application for this property.", 409)

    message = str(data.get("message") or "").strip()
    if len(message) > 2000:
        return error("Your application message must be 2,000 characters or fewer.")

    application = PropertyApplication(
        property_id=prop.id,
        tenant_id=tenant.id,
        message=message or None,
        status="pending",
    )
    db.session.add(application)
    db.session.commit()

    landlord = db.session.get(User, prop.landlord_id)
    if landlord:
        notify(
            landlord,
            "New property application",
            f"{tenant.full_name} has applied for {prop.name}. Sign in to Cribsy to review the application.",
        )

    return jsonify(application.to_dict()), 201


@bp.get("/tenant/applications")
@roles_required("tenant")
def tenant_applications():
    tenant = current_user()
    applications = (
        PropertyApplication.query
        .filter_by(tenant_id=tenant.id)
        .order_by(PropertyApplication.created_at.desc())
        .all()
    )
    return jsonify([item.to_dict() for item in applications])


# ---------------- LANDLORD APPLICATION REVIEWS ----------------

@bp.get("/landlord/applications")
@roles_required("landlord")
def landlord_applications():
    landlord = current_user()
    query = (
        PropertyApplication.query
        .join(Property, PropertyApplication.property_id == Property.id)
        .filter(Property.landlord_id == landlord.id)
    )

    status = request.args.get("status")
    if status in ("pending", "approved", "rejected"):
        query = query.filter(PropertyApplication.status == status)

    applications = query.order_by(PropertyApplication.created_at.desc()).all()
    return jsonify([item.to_dict() for item in applications])


@bp.patch("/landlord/applications/<int:application_id>")
@roles_required("landlord")
def review_application(application_id):
    landlord = current_user()
    application = (
        PropertyApplication.query
        .join(Property, PropertyApplication.property_id == Property.id)
        .filter(
            PropertyApplication.id == application_id,
            Property.landlord_id == landlord.id,
        )
        .first()
    )

    if application is None:
        return error("Application not found.", 404)

    if application.status != "pending":
        return error("This application has already been reviewed.", 409)

    status = json_body().get("status")
    if status not in ("approved", "rejected"):
        return error("Choose approved or rejected.")

    application.status = status
    application.reviewed_by = landlord.id
    application.reviewed_at = utcnow()
    db.session.commit()

    notify(
        application.tenant,
        f"Your application was {status}",
        f"Your application for {application.property.name} has been {status}. Sign in to Cribsy to view its status.",
    )

    return jsonify(application.to_dict())


# ---------------- LANDLORD PROPERTY UNITS ----------------

@bp.get("/landlord/properties/<int:property_id>/units")
@roles_required("landlord")
def list_property_units(property_id):
    prop = landlord_property_or_404(property_id, current_user())
    if prop is None:
        return error("Property not found.", 404)

    return jsonify([unit.to_dict() for unit in prop.units])


@bp.post("/landlord/properties/<int:property_id>/units")
@roles_required("landlord")
def create_property_unit(property_id):
    prop = landlord_property_or_404(property_id, current_user())
    if prop is None:
        return error("Property not found.", 404)

    if prop.approval_status != "approved":
        return error("Only approved properties can have rentable units.", 409)

    data = json_body()
    unit_number = str(data.get("unit_number") or "").strip()
    rent = to_int(data.get("monthly_rent"))
    bedrooms = to_int(data.get("bedrooms", 0))
    bathrooms = to_int(data.get("bathrooms", 0))

    fields = {}
    if not unit_number or len(unit_number) > 80:
        fields["unit_number"] = "Enter a unit number of up to 80 characters."
    if rent is None or rent <= 0:
        fields["monthly_rent"] = "Enter a valid monthly rent."
    if bedrooms is None or bedrooms < 0:
        fields["bedrooms"] = "Enter a valid bedroom count."
    if bathrooms is None or bathrooms < 0:
        fields["bathrooms"] = "Enter a valid bathroom count."
    if fields:
        return error("Please correct the unit details.", 400, fields=fields)

    unit = PropertyUnit(
        property_id=prop.id,
        unit_number=unit_number,
        monthly_rent=rent,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        description=str(data.get("description") or "").strip() or None,
        status="available",
    )
    db.session.add(unit)

    try:
        db.session.flush()
        update_property_availability(prop)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("A unit with that number already exists for this property.", 409)

    return jsonify(unit.to_dict()), 201


# ---------------- ASSIGN AN APPROVED APPLICANT ----------------

@bp.post("/landlord/applications/<int:application_id>/assign")
@roles_required("landlord")
def assign_approved_applicant(application_id):
    landlord = current_user()
    data = json_body()

    application = (
        PropertyApplication.query
        .join(Property, PropertyApplication.property_id == Property.id)
        .filter(
            PropertyApplication.id == application_id,
            Property.landlord_id == landlord.id,
        )
        .first()
    )

    if application is None:
        return error("Application not found.", 404)

    if application.status != "approved":
        return error("Approve this application before assigning a unit.", 409)

    if Tenancy.query.filter(
        Tenancy.tenant_id == application.tenant_id,
        Tenancy.status.in_(ACTIVE_TENANCY),
    ).first():
        return error("This applicant already has an active tenancy.", 409)

    unit_id = to_int(data.get("unit_id"))
    start = parse_date(data.get("start_date"))
    end = parse_date(data.get("end_date"))

    fields = {}
    if unit_id is None:
        fields["unit_id"] = "Choose a unit."
    if start is None:
        fields["start_date"] = "Use the format YYYY-MM-DD."
    if end is None:
        fields["end_date"] = "Use the format YYYY-MM-DD."
    if start and end and end <= start:
        fields["end_date"] = "The end date must be after the start date."
    if fields:
        return error("Please correct the assignment details.", 400, fields=fields)

    unit = PropertyUnit.query.filter_by(
        id=unit_id,
        property_id=application.property_id,
    ).first()

    if unit is None:
        return error("The selected unit does not belong to this property.", 404)

    if any(t.status in ACTIVE_TENANCY for t in unit.tenancies):
        return error("This unit is already occupied.", 409)

    tenancy = Tenancy(
        tenant_id=application.tenant_id,
        property_id=application.property_id,
        unit_id=unit.id,
        start_date=start,
        end_date=end,
        status="active",
        monthly_rent=unit.monthly_rent,
    )

    db.session.add(tenancy)
    update_property_availability(application.property)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("The assignment could not be completed. Refresh and try again.", 409)

    notify(
        application.tenant,
        "You have been assigned a unit",
        f"You have been assigned unit {unit.unit_number} at {application.property.name}. Sign in to Cribsy to view your tenancy.",
    )

    return jsonify({
        "message": "Applicant successfully assigned to the unit.",
        "tenancy": tenancy.to_dict(),
        "application": application.to_dict(),
    }), 201
