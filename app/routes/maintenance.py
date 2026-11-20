"""OWNER: Member 6 (Lynn). Maintenance requests: tenants report issues, landlords follow them up."""
from flask import Blueprint, abort, jsonify, request
from email_service import send_email
from ..extension import db
from ..models import (
    MAINTENANCE_CATEGORIES, MAINTENANCE_STATUSES, MaintenancePhoto, MaintenanceRequest, Property, Tenancy,
)
from ..uploads import is_valid_image_url
from ..utils import active_tenancy_for, current_user, error, json_body, notify, roles_required

bp = Blueprint("maintenance", __name__)
URL_PREFIX = "/api"

MAX_PHOTOS = 4


# ---------- tenant side ----------
@bp.post("/tenant/maintenance")
@roles_required("tenant")
def create_request():
    user = current_user()
    tenancy = active_tenancy_for(user)
    if tenancy is None:
        return error("You need an active tenancy before you can report an issue.", 400)

    data = json_body()
    category = data.get("category")
    description = str(data.get("description") or "").strip()
    photo_urls = data.get("photo_urls") or []

    fields = {}
    if category not in MAINTENANCE_CATEGORIES:
        fields["category"] = f"Choose one of: {', '.join(MAINTENANCE_CATEGORIES)}."
    if len(description) < 15:
        fields["description"] = "Describe the problem in at least 15 characters."
    if not isinstance(photo_urls, list) or len(photo_urls) > MAX_PHOTOS:
        fields["photo_urls"] = f"Send a list of at most {MAX_PHOTOS} photo links."
    elif not all(is_valid_image_url(url) for url in photo_urls):
        fields["photo_urls"] = "Upload each photo first and use the links you get back."
    if fields:
        return error("Please fix the highlighted fields.", 400, fields=fields)

    request_row = MaintenanceRequest(tenancy_id=tenancy.id, category=category, description=description)
    for url in photo_urls:
        request_row.photos.append(MaintenancePhoto(file_url=str(url)))
    db.session.add(request_row)
    db.session.commit()

    landlord = tenancy.property.landlord

    notify(
        landlord,
        f"New maintenance request: {category}",
        f"{user.full_name} reported an issue at "
        f"{tenancy.property.name}:\n\n{description}"
    )

    # Email notification to landlord
    landlord_email = getattr(landlord, "email", None)

    if landlord_email:
        send_email(
            to_email=landlord_email,
            subject=f"Cribsy - New Maintenance Request: {category}",
            html_content=f"""
                <h2>New Maintenance Request</h2>
                <p>Hello {landlord.full_name},</p>
                <p>A tenant has submitted a maintenance request.</p>
                <p><strong>Tenant:</strong> {user.full_name}</p>
                <p><strong>Property:</strong> {tenancy.property.name}</p>
                <p><strong>Category:</strong> {category}</p>
                <p><strong>Description:</strong> {description}</p>
            """
        )

    return jsonify(request_row.to_dict()), 201


@bp.get("/tenant/maintenance")
@roles_required("tenant")
def my_requests():
    rows = (
        MaintenanceRequest.query.join(Tenancy)
        .filter(Tenancy.tenant_id == current_user().id)
        .order_by(MaintenanceRequest.id.desc())
        .all()
    )
    return jsonify([r.to_dict() for r in rows])


@bp.get("/tenant/maintenance/<int:request_id>")
@roles_required("tenant")
def my_request_details(request_id):
    row = db.get_or_404(MaintenanceRequest, request_id)
    if row.tenancy.tenant_id != current_user().id:
        abort(404)
    return jsonify(row.to_dict())


# ---------- landlord side ----------
def landlord_request_or_404(request_id, user):
    row = db.get_or_404(MaintenanceRequest, request_id)
    if row.tenancy.property.landlord_id != user.id:
        abort(404)
    return row


@bp.get("/landlord/maintenance")
@roles_required("landlord")
def landlord_requests():
    query = (
        MaintenanceRequest.query.join(Tenancy)
        .join(Property, Tenancy.property_id == Property.id)
        .filter(Property.landlord_id == current_user().id)
    )
    status = request.args.get("status")
    if status:
        query = query.filter(MaintenanceRequest.status == status)
    return jsonify([r.to_dict() for r in query.order_by(MaintenanceRequest.id.desc()).all()])


@bp.get("/landlord/maintenance/<int:request_id>")
@roles_required("landlord")
def landlord_request_details(request_id):
    return jsonify(landlord_request_or_404(request_id, current_user()).to_dict())


@bp.patch("/landlord/maintenance/<int:request_id>")
@roles_required("landlord")
def update_request_status(request_id):
    row = landlord_request_or_404(request_id, current_user())
    status = json_body().get("status")
    if status not in MAINTENANCE_STATUSES:
        return error(f"Status must be one of: {', '.join(MAINTENANCE_STATUSES)}.", 400)

    row.status = status
    db.session.commit()

    
    # Existing in-app notification to tenant
    tenant = row.tenancy.tenant

    notify(
        tenant,
        "Your maintenance request was updated",
        f"Your {row.category} request at "
        f"{row.tenancy.property.name} is now: "
        f"{status.replace('_', ' ')}."
    )

    # Email notification to tenant
    tenant_email = getattr(tenant, "email", None)

    if tenant_email:
        send_email(
            to_email=tenant_email,
            subject="Cribsy - Maintenance Request Update",
            html_content=f"""
                <h2>Maintenance Request Update</h2>
                <p>Hello {tenant.full_name},</p>
                <p>Your maintenance request has been updated.</p>
                <p><strong>Property:</strong> {row.tenancy.property.name}</p>
                <p><strong>Category:</strong> {row.category}</p>
                <p><strong>New status:</strong> {row.status.replace('_', ' ')}</p>
                <p>Thank you for using Cribsy!</p>
            """
        )

    return jsonify(row.to_dict())

