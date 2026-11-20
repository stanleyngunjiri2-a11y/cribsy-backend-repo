import secrets
from datetime import date
from email_service import send_email

from flask import Blueprint, abort, jsonify, request
import logging

logger = logging.getLogger(__name__)

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

    notify(
    tenancy.tenant,
    "Rent payment recorded",
    f"A {status} payment of KSh {amount:,} was recorded for "
    f"{tenancy.property.name}. Reference: {reference}."
    )

    # Send receipt only for confirmed payments
    if status == "paid":
        tenant_email = getattr(tenancy.tenant, "email", None)

        send_email(
        to_email=tenant_email,
        subject="Cribsy - Rent Payment Receipt",
        html_content=f"""
            <h2>Payment Confirmation</h2>
            <p>Hello {tenancy.tenant.full_name},</p>
            <p>Your rent payment has been recorded successfully.</p>
            <p><strong>Property:</strong> {tenancy.property.name}</p>
            <p><strong>Amount:</strong> KSh {amount:,}</p>
            <p><strong>Payment date:</strong> {paid_on}</p>
            <p><strong>Method:</strong> {method}</p>
            <p><strong>Reference:</strong> {reference}</p>
            <p>Thank you for using Cribsy!</p>
        """
    )
    return jsonify(payment.to_dict()), 201



@bp.patch("/payments/<int:payment_id>")
@roles_required("landlord")
def update_payment(payment_id):
    payment = db.get_or_404(RentPayment, payment_id)

    if payment.tenancy.property.landlord_id != current_user().id:
        abort(404)

    status = json_body().get("status")

    if status not in PAYMENT_STATUSES:
        return error(
            f"Status must be one of: {', '.join(PAYMENT_STATUSES)}.",
            400
        )

    old_status = payment.status

    payment.status = status
    db.session.commit()

    # Only send an email when the payment becomes paid
    if old_status != "paid" and status == "paid":
        tenant = payment.tenancy.tenant

        email_sent = send_email(
            to_email=getattr(tenant, "email", None),
            subject="Cribsy - Payment Confirmed",
            html_content=f"""
                <h2>Payment Confirmed!</h2>
                <p>Hello {tenant.full_name},</p>
                <p>Your rent payment has been confirmed.</p>
                <p><strong>Amount:</strong> KSh {payment.amount:,}</p>
                <p><strong>Reference:</strong> {payment.reference}</p>
                <p>Thank you for using Cribsy!</p>
            """
        )

        if not email_sent:
            logger.warning(
                "Payment confirmation email could not be sent "
                "for payment ID %s", payment.id
            )

    return jsonify(payment.to_dict())
