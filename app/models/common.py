"""OWNER: Member 1 (Stanley). Shared constants and helpers used by every model file."""
from datetime import datetime, timezone

# Allowed values (also useful for dropdowns on the frontend)
ROLES = ("tenant", "landlord", "admin")
USER_STATUSES = ("active", "suspended")
PROPERTY_TYPES = ("Apartment", "House", "Bedsitter", "Studio")
AVAILABILITY = ("vacant", "occupied")
APPROVALS = ("pending", "approved", "rejected")
TENANCY_STATUSES = ("active", "notice", "ended")
ACTIVE_TENANCY = ("active", "notice")  # a tenant still living in the property
PAYMENT_STATUSES = ("paid", "pending", "overdue")
PAYMENT_METHODS = ("Mobile money", "Bank transfer", "Cash")
MAINTENANCE_STATUSES = ("pending", "in_progress", "resolved", "rejected")
MAINTENANCE_CATEGORIES = (
    "Plumbing", "Electrical", "Appliances", "Doors and locks", "Pests", "Structural", "Other",
)


def utcnow():
    """Current UTC time without timezone info (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    return value.isoformat() if value else None
