"""OWNER: Member 6 (Lynn). Administrator tools: users and property approval."""
from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import APPROVALS, USER_STATUSES, Property, User
from ..utils import current_user, error, json_body, notify, roles_required

bp = Blueprint("admin", __name__)
URL_PREFIX = "/api/admin"


@bp.get("/stats")
@roles_required("admin")
def stats():
    return jsonify({
        "total_users": User.query.count(),
        "landlords": User.query.filter_by(role="landlord").count(),
        "tenants": User.query.filter_by(role="tenant").count(),
        "properties_pending_approval": Property.query.filter_by(approval_status="pending").count(),
    })


@bp.get("/users")
@roles_required("admin")
def list_users():
    query = User.query
    role = request.args.get("role")
    status = request.args.get("status")
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    return jsonify([u.to_dict() for u in query.order_by(User.id).all()])


@bp.patch("/users/<int:user_id>/status")
@roles_required("admin")
def set_user_status(user_id):
    user = db.get_or_404(User, user_id)
    status = json_body().get("status")
    if status not in USER_STATUSES:
        return error(f"Status must be one of: {', '.join(USER_STATUSES)}.", 400)
    if user.id == current_user().id or user.role == "admin":
        return error("Administrator accounts cannot be suspended here.", 403)

    user.status = status
    db.session.commit()
    return jsonify(user.to_dict())


@bp.get("/properties")
@roles_required("admin")
def list_properties():
    query = Property.query
    approval = request.args.get("approval_status")
    if approval:
        query = query.filter(Property.approval_status == approval)
    return jsonify([p.to_dict(include_landlord=True) for p in query.order_by(Property.id).all()])


@bp.patch("/properties/<int:property_id>/approval")
@roles_required("admin")
def set_approval(property_id):
    prop = db.get_or_404(Property, property_id)
    approval = json_body().get("approval_status")
    if approval not in APPROVALS:
        return error(f"approval_status must be one of: {', '.join(APPROVALS)}.", 400)

    prop.approval_status = approval
    db.session.commit()

    notify(prop.landlord, f"Your property was {approval}", f"{prop.name} is now marked as: {approval}.")
    return jsonify(prop.to_dict(include_landlord=True))
