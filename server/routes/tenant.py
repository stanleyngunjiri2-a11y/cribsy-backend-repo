from flask import Blueprint, abort, jsonify

from ..extension import db
from ..models import MaintenanceRequest, RentPayment, Tenancy
from ..utils import active_tenancy_for, current_user, roles_required

bp = Blueprint("tenant", __name__)
URL_PREFIX = "/api/tenant"


def my_payments_query(user):
    return RentPayment.query.join(Tenancy).filter(Tenancy.tenant_id == user.id)


@bp.get("/tenancy")
@roles_required("tenant")
def my_tenancy():
    tenancy = active_tenancy_for(current_user())
    return jsonify({"tenancy": tenancy.to_dict() if tenancy else None})


@bp.get("/dashboard")
@roles_required("tenant")
def dashboard():
    user = current_user()
    tenancy = active_tenancy_for(user)
    recent = my_payments_query(user).order_by(RentPayment.paid_on.desc(), RentPayment.id.desc()).limit(3).all()
    requests = (
        MaintenanceRequest.query.join(Tenancy)
        .filter(Tenancy.tenant_id == user.id)
        .order_by(MaintenanceRequest.id.desc())
        .limit(5)
        .all()
    )
    return jsonify({
        "tenancy": tenancy.to_dict() if tenancy else None,
        "recent_payments": [p.to_dict() for p in recent],
        "maintenance_requests": [m.to_dict() for m in requests],
    })


@bp.get("/payments")
@roles_required("tenant")
def rent_history():
    payments = my_payments_query(current_user()).order_by(RentPayment.paid_on.desc(), RentPayment.id.desc()).all()
    return jsonify([p.to_dict() for p in payments])


@bp.get("/payments/<int:payment_id>")
@roles_required("tenant")
def payment_details(payment_id):
    payment = db.get_or_404(RentPayment, payment_id)
    if payment.tenancy.tenant_id != current_user().id:
        abort(404)
    return jsonify(payment.to_dict())
