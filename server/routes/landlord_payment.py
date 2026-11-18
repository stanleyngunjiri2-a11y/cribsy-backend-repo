import secrets
from datetime import date

from flask import Blueprint, abort, jsonify, request

from ..extension import db
from ..models import PAYMENT_METHODS, PAYMENT_STATUSES, Property, RentPayment, Tenancy
from ..utils import current_user, error, json_body, notify, parse_date, roles_required, to_int

bp = Blueprint("landlord_payments", __name__)
URL_PREFIX = "/api/landlord"


def my_property_ids(user):
    return [p.id for p in Property.query.filter_by(landlord_id=user.id).all()]


def own_tenancy_or_404(tenancy_id, user):
    tenancy = db.get_or_404(Tenancy, tenancy_id)
    if tenancy.property.landlord_id != user.id:
        abort(404)
    return tenancy


@bp.get("/payments")
@roles_required("landlord")
def list_payments():
    query = RentPayment.query.join(Tenancy).filter(Tenancy.property_id.in_(my_property_ids(current_user())))
    tenancy_id = request.args.get("tenancy_id", type=int)
    if tenancy_id:
        query = query.filter(RentPayment.tenancy_id == tenancy_id)
    payments = query.order_by(RentPayment.paid_on.desc(), RentPayment.id.desc()).all()
    return jsonify([p.to_dict() for p in payments])


@bp.post("/tenancies/<int:tenancy_id>/payments")
@roles_required("landlord")
def record_payment(tenancy_id):
    tenancy = own_tenancy_or_404(tenancy_id, current_user())
    data = json_body()
    fields = {}

    amount = to_int(data.get("amount"))
    if amount is None or amount <= 0:
        fields["amount"] = "Enter an amount above 0."

    paid_on = parse_date(data.get("paid_on")) if data.get("paid_on") else date.today()
    if paid_on is None:
        fields["paid_on"] = "Use the format YYYY-MM-DD."

    method = data.get("method", "Mobile money")
    if method not in PAYMENT_METHODS:
        fields["method"] = f"Must be one of: {', '.join(PAYMENT_METHODS)}."

    status = data.get("status", "paid")
    if status not in PAYMENT_STATUSES:
        fields["status"] = f"Must be one of: {', '.join(PAYMENT_STATUSES)}."

    reference = str(data.get("reference") or "").strip()
    if not reference and paid_on:
        reference = f"RC-{paid_on:%Y%m%d}-{secrets.token_hex(3).upper()}"
    if reference and RentPayment.query.filter_by(reference=reference).first():
        fields["reference"] = "This reference already exists."

    if fields:
        return error("Please fix the highlighted fields.", 400, fields=fields)

    payment = RentPayment(tenancy_id=tenancy.id, amount=amount, paid_on=paid_on,
                          reference=reference, method=method, status=status)
    db.session.add(payment)
    db.session.commit()

    notify(tenancy.tenant, "Rent payment recorded",
           f"A {status} payment of KSh {amount:,} was recorded for {tenancy.property.name}. Reference: {reference}.")
    return jsonify(payment.to_dict()), 201


@bp.patch("/payments/<int:payment_id>")
@roles_required("landlord")
def update_payment(payment_id):
    payment = db.get_or_404(RentPayment, payment_id)
    if payment.tenancy.property.landlord_id != current_user().id:
        abort(404)

    status = json_body().get("status")
    if status not in PAYMENT_STATUSES:
        return error(f"Status must be one of: {', '.join(PAYMENT_STATUSES)}.", 400)
    payment.status = status
    db.session.commit()
    return jsonify(payment.to_dict())
