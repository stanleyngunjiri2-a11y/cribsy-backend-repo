from flask import Blueprint, jsonify, request

from server.extension import db
from server.models.enquiry import Enquiry

enquiries_bp = Blueprint("enquiries", __name__, url_prefix="/enquiries")


@enquiries_bp.route("", methods=["GET"])
def list_enquiries():
    property_id = request.args.get("property_id", type=int)
    query = Enquiry.query
    if property_id:
        query = query.filter_by(property_id=property_id)
    enquiries = query.order_by(Enquiry.created_at.desc()).all()
    return jsonify([e.to_dict() for e in enquiries]), 200


@enquiries_bp.route("/<int:enquiry_id>", methods=["GET"])
def get_enquiry(enquiry_id):
    enquiry = db.get_or_404(Enquiry, enquiry_id)
    return jsonify(enquiry.to_dict()), 200


@enquiries_bp.route("", methods=["POST"])
def create_enquiry():
    data = request.get_json(silent=True) or {}
    required = ["property_id", "name", "email", "message"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    enquiry = Enquiry(
        property_id=data["property_id"],
        name=data["name"],
        email=data["email"],
        message=data["message"],
    )
    db.session.add(enquiry)
    db.session.commit()
    return jsonify(enquiry.to_dict()), 201


@enquiries_bp.route("/<int:enquiry_id>", methods=["DELETE"])
def delete_enquiry(enquiry_id):
    enquiry = db.get_or_404(Enquiry, enquiry_id)
    db.session.delete(enquiry)
    db.session.commit()
    return "", 204