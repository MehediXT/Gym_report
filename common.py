"""
Shared helpers used by both storage backends (MySQL and JSON fallback):
input validation, subscription status classification, date arithmetic,
and role-based permissions.
"""

import re
import hashlib
from datetime import datetime, date, timedelta

PAYMENT_METHODS = ["Cash", "Credit Card", "Debit Card", "Bank Transfer", "UPI / Digital"]
GENDERS = ["Male", "Female", "Other"]
EXPIRING_SOON_DAYS = 7


def hash_password(password: str) -> str:
    """Hash password using SHA-256 (matches MySQL SHA2(pwd, 256))."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# -------------------------------------------------------------
# Validation (domain integrity checks before data reaches storage)
# -------------------------------------------------------------
_PHONE_CHARS = re.compile(r"\+?[0-9][0-9\- ()]*")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")


def validate_phone(phone, field="Phone"):
    """Allow digits, spaces, dashes, brackets and a leading '+'; 7-15 digits total."""
    p = (phone or "").strip()
    if not p:
        raise ValueError(f"Validation Error: {field} is required.")
    digits = re.sub(r"\D", "", p)
    if not _PHONE_CHARS.fullmatch(p) or not 7 <= len(digits) <= 15:
        raise ValueError(
            f"Validation Error: {field} '{p}' is invalid. Use 7-15 digits, "
            f"optionally with a leading '+', spaces or dashes (e.g. +880 1712-345678)."
        )
    return p


def validate_email(email):
    e = (email or "").strip()
    if not _EMAIL.fullmatch(e):
        raise ValueError(f"Validation Error: Email '{e}' is not a valid email address.")
    return e


def validate_date(value, field="Date"):
    s = str(value or "").strip()
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Validation Error: {field} '{s}' must use the YYYY-MM-DD format.")
    return s


def validate_required(value, field):
    v = (value or "").strip()
    if not v:
        raise ValueError(f"Validation Error: {field} is required.")
    return v


def validate_member_fields(full_name, phone, email, gender, join_date,
                           emergency_contact_name="", emergency_contact_phone=""):
    """Validate and normalise every member field. Returns a dict of clean values."""
    name = validate_required(full_name, "Full name")
    phone = validate_phone(phone)
    email = validate_email(email)
    gender = (gender or "").strip()
    if gender not in GENDERS:
        raise ValueError(f"Validation Error: Gender must be one of {', '.join(GENDERS)}.")
    join_date = validate_date(join_date, "Join date")
    ec_name = (emergency_contact_name or "").strip()
    ec_phone = (emergency_contact_phone or "").strip()
    if ec_phone:
        ec_phone = validate_phone(ec_phone, "Emergency contact phone")
        if ec_phone == phone:
            raise ValueError("Validation Error: Emergency contact phone must differ from the member's own phone.")
    if bool(ec_name) != bool(ec_phone):
        raise ValueError("Validation Error: Provide both emergency contact name and phone, or leave both empty.")
    return {
        "full_name": name, "phone": phone, "email": email, "gender": gender,
        "join_date": join_date,
        "emergency_contact_name": ec_name, "emergency_contact_phone": ec_phone,
    }


# -------------------------------------------------------------
# Subscription lifecycle helpers
# -------------------------------------------------------------
def to_date(value):
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def compute_subscription_status(end_date_value):
    """
    Classify a subscription by its end date:
    - 'Active'        (days_left > 7)
    - 'Expiring Soon' (0 <= days_left <= 7)
    - 'Expired'       (days_left < 0)
    - 'No Subscription' when there is no end date
    """
    if not end_date_value or end_date_value == "-":
        return "No Subscription", None
    try:
        days_left = (to_date(end_date_value) - date.today()).days
    except Exception:
        return "Unknown", None
    if days_left > EXPIRING_SOON_DAYS:
        return "Active", days_left
    if days_left >= 0:
        return "Expiring Soon", days_left
    return "Expired", days_left


def calculate_end_date(start_date_value, duration_days):
    """Python equivalent of SQL DATE_ADD(start_date, INTERVAL duration_days DAY)."""
    return (to_date(start_date_value) + timedelta(days=int(duration_days))).strftime("%Y-%m-%d")


def last_n_months(n=6):
    """Return the last n month keys ('YYYY-MM'), oldest first, ending with the current month."""
    today = date.today()
    year, month = today.year, today.month
    keys = []
    for _ in range(n):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(keys))


def validate_payment(amount_paid, payment_method):
    try:
        amount = float(amount_paid)
    except (TypeError, ValueError):
        raise ValueError("Validation Error: Amount paid must be a number.")
    if amount < 0:
        raise ValueError("Validation Error: Amount paid cannot be negative.")
    method = (payment_method or "").strip()
    if method not in PAYMENT_METHODS:
        raise ValueError(f"Validation Error: Payment method must be one of {', '.join(PAYMENT_METHODS)}.")
    return amount, method


def validate_trainer_fields(full_name, phone, specialization, monthly_salary, hire_date):
    name = validate_required(full_name, "Trainer name")
    phone = validate_phone(phone)
    spec = validate_required(specialization, "Specialization")
    try:
        salary = float(monthly_salary)
    except (TypeError, ValueError):
        raise ValueError("Validation Error: Monthly salary must be a number.")
    if salary <= 0:
        raise ValueError("Validation Error: Trainer monthly salary must be greater than 0.")
    hire_date = validate_date(hire_date, "Hire date")
    return {"full_name": name, "phone": phone, "specialization": spec,
            "monthly_salary": salary, "hire_date": hire_date}


def validate_package_fields(package_name, duration_days, fee, description):
    name = validate_required(package_name, "Package name")
    try:
        duration = int(duration_days)
    except (TypeError, ValueError):
        raise ValueError("Validation Error: Duration must be a whole number of days.")
    if duration <= 0:
        raise ValueError("Validation Error: Duration must be at least 1 day.")
    try:
        fee = float(fee)
    except (TypeError, ValueError):
        raise ValueError("Validation Error: Fee must be a number.")
    if fee < 0:
        raise ValueError("Validation Error: Package fee cannot be negative.")
    return {"package_name": name, "duration_days": duration, "fee": fee,
            "description": (description or "").strip()}


# -------------------------------------------------------------
# Role-based access control
# -------------------------------------------------------------
ROLE_PERMISSIONS = {
    "Admin": {"*"},
    "Manager": {
        "member.add", "member.edit", "member.delete",
        "trainer.add", "trainer.edit", "trainer.delete",
        "package.add", "package.edit", "package.delete",
        "billing.record", "billing.void",
        "audit.view", "data.export",
    },
    "Staff": {
        "member.add", "member.edit",
        "billing.record",
    },
}


def role_can(role, permission):
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms
