"""
MySQL / MariaDB data access layer.

Implements the same public interface as the JSON fallback in database.py,
but every operation is a real, parameterized SQL statement (%s placeholders)
executed through mysql-connector-python:

- Constraints (PK, FK, UNIQUE, CHECK, ENUM) are enforced by the database (sql/schema.sql)
- ON DELETE CASCADE / SET NULL / RESTRICT are handled by InnoDB foreign keys
- end_date is computed with DATE_ADD(), remaining days with DATEDIFF(CURDATE(), ...)
- Reports use JOINs, views, GROUP BY / HAVING and aggregate functions
"""

import os
import re
from datetime import date, datetime
from decimal import Decimal

import mysql.connector
from mysql.connector import Error as MySQLError

from common import (
    validate_member_fields, validate_trainer_fields, validate_package_fields,
    validate_payment, validate_date, compute_subscription_status,
    calculate_end_date, last_n_months,
)

SQL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sql")

# MySQL / MariaDB error numbers we translate into friendly messages
ER_DUP_ENTRY = 1062
ER_ROW_IS_REFERENCED = (1451, 1217)
ER_NO_REFERENCED_ROW = (1452, 1216)
ER_CHECK_CONSTRAINT = (3819, 4025)

# Derived subscription status, shared by several queries (s = subscriptions alias)
STATUS_CASE = """
    CASE
        WHEN DATEDIFF(s.end_date, CURDATE()) > 7  THEN 'Active'
        WHEN DATEDIFF(s.end_date, CURDATE()) >= 0 THEN 'Expiring Soon'
        ELSE 'Expired'
    END
"""

DUPLICATE_KEY_MESSAGES = {
    "uq_users_username": "Username already exists.",
    "uq_trainers_phone": "This phone number is already used by another trainer.",
    "uq_members_phone": "This phone number is already used by another member.",
    "uq_packages_name": "A package with this name already exists.",
}


def _split_sql(script):
    """Split a .sql file into statements (our scripts never contain ';' inside strings)."""
    script = re.sub(r"(^|\s)--[^\n]*", r"\1", script)
    return [stmt.strip() for stmt in script.split(";") if stmt.strip()]


def _clean(row):
    """Convert DB types into the plain Python types the UI expects."""
    out = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, datetime):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, date):
            value = value.strftime("%Y-%m-%d")
        elif isinstance(value, (bytes, bytearray)):
            value = value.decode("utf-8")
        out[key] = value
    return out


def _friendly_error(err):
    """Turn a MySQL constraint error into a ValueError with a readable message."""
    msg = str(getattr(err, "msg", err))
    if err.errno == ER_DUP_ENTRY:
        for key, text in DUPLICATE_KEY_MESSAGES.items():
            if key in msg:
                return ValueError(f"Constraint Violation (UNIQUE): {text}")
        return ValueError(f"Constraint Violation (UNIQUE): {msg}")
    if err.errno in ER_ROW_IS_REFERENCED:
        return ValueError(f"Referential Integrity Restriction (ON DELETE RESTRICT): {msg}")
    if err.errno in ER_NO_REFERENCED_ROW:
        return ValueError(f"Referential Integrity Violation (FOREIGN KEY): referenced record does not exist. {msg}")
    if err.errno in ER_CHECK_CONSTRAINT:
        return ValueError(f"Constraint Violation (CHECK): {msg}")
    return ValueError(f"Database Error {err.errno}: {msg}")


class MySQLGymDatabase:
    backend_name = "MySQL"

    def __init__(self, host="localhost", port=3306, user="gym_app", password="",
                 database="gym_db", unix_socket=None, **_ignored):
        params = {
            "host": host, "port": int(port), "user": user, "password": password,
            "database": database, "autocommit": False, "charset": "utf8mb4",
            "use_pure": True, "connection_timeout": 5,
        }
        if unix_socket:
            params["unix_socket"] = unix_socket
        self.conn = mysql.connector.connect(**params)
        self.database = database
        self.backend_label = f"MySQL · {database}@{host}"
        self.app_user = None
        self.triggers_enabled = False
        self._ensure_schema()

    # -------------------------------------------------------------
    # Low-level helpers
    # -------------------------------------------------------------
    def _cursor(self, dictionary=True):
        self.conn.ping(reconnect=True, attempts=2, delay=0)
        return self.conn.cursor(dictionary=dictionary)

    def _query(self, sql, params=None):
        cur = self._cursor()
        try:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            rows = [_clean(r) for r in cur.fetchall()]
            self.conn.commit()  # end the read transaction so later reads see fresh data
            return rows
        finally:
            cur.close()

    def _query_one(self, sql, params=None):
        rows = self._query(sql, params)
        return rows[0] if rows else None

    def _scalar(self, sql, params=None):
        row = self._query_one(sql, params)
        return next(iter(row.values())) if row else None

    def _execute(self, sql, params=None):
        """Run one write statement in its own transaction. Returns (lastrowid, rowcount)."""
        cur = self._cursor()
        try:
            # Tell the audit triggers who is making this change
            cur.execute("SET @app_user = %s", (self.app_user,))
            cur.execute(sql, params or ())
            self.conn.commit()
            return cur.lastrowid, cur.rowcount
        except MySQLError as err:
            self.conn.rollback()
            raise _friendly_error(err) from err
        finally:
            cur.close()

    def _run_script(self, filename):
        with open(os.path.join(SQL_DIR, filename), "r", encoding="utf-8") as f:
            statements = _split_sql(f.read())
        cur = self._cursor(dictionary=False)
        try:
            for stmt in statements:
                cur.execute(stmt)
            self.conn.commit()
        except MySQLError:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    def _ensure_schema(self):
        """Create tables/views/triggers if missing (idempotent) and seed an empty database."""
        self._run_script("schema.sql")
        try:
            self._run_script("triggers.sql")
            self.triggers_enabled = True
        except MySQLError as err:
            print(f"[IronPulse] Audit triggers not installed ({err}). The activity log will stay empty.")
        if not self._scalar("SELECT COUNT(*) FROM users"):
            self.reset_to_demo_data()

    def reset_to_demo_data(self):
        self._run_script("seed.sql")
        if self.app_user:
            self._execute(
                "UPDATE audit_log SET app_user = %s, details = %s WHERE action = 'DEMO_RESET'",
                (self.app_user, "Demo data restored with the Reset button"),
            )

    def set_session_user(self, username):
        """Remember the signed-in staff user; written to @app_user before every change."""
        self.app_user = username

    # Static helpers shared with the JSON backend (used for live previews in dialogs)
    compute_subscription_status = staticmethod(compute_subscription_status)
    calculate_end_date = staticmethod(calculate_end_date)

    # -------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------
    def authenticate(self, username, password):
        return self._query_one(
            "SELECT user_id, username, role, full_name FROM users "
            "WHERE username = %s AND password_hash = SHA2(%s, 256)",
            (username.strip(), password),
        )

    # -------------------------------------------------------------
    # Trainers
    # -------------------------------------------------------------
    def get_all_trainers(self):
        """Trainer list with workload: COUNT/SUM over a LEFT JOIN, grouped per trainer."""
        rows = self._query("""
            SELECT t.trainer_id, t.full_name, t.phone, t.specialization,
                   t.monthly_salary, t.hire_date,
                   COUNT(mo.member_id)                                         AS assigned_count,
                   COALESCE(SUM(mo.status IN ('Active', 'Expiring Soon')), 0)  AS active_count,
                   GROUP_CONCAT(mo.full_name ORDER BY mo.full_name SEPARATOR '||') AS assigned_members
            FROM trainers t
            LEFT JOIN v_member_overview mo ON mo.trainer_id = t.trainer_id
            GROUP BY t.trainer_id, t.full_name, t.phone, t.specialization,
                     t.monthly_salary, t.hire_date
            ORDER BY t.trainer_id
        """)
        for r in rows:
            r["assigned_count"] = int(r["assigned_count"])
            r["active_count"] = int(r["active_count"])
            r["assigned_members"] = r["assigned_members"].split("||") if r["assigned_members"] else []
        return rows

    def get_trainer_by_id(self, trainer_id):
        return self._query_one("SELECT * FROM trainers WHERE trainer_id = %s", (trainer_id,))

    def add_trainer(self, full_name, phone, specialization, monthly_salary, hire_date):
        v = validate_trainer_fields(full_name, phone, specialization, monthly_salary, hire_date)
        new_id, _ = self._execute(
            "INSERT INTO trainers (full_name, phone, specialization, monthly_salary, hire_date) "
            "VALUES (%s, %s, %s, %s, %s)",
            (v["full_name"], v["phone"], v["specialization"], v["monthly_salary"], v["hire_date"]),
        )
        return self.get_trainer_by_id(new_id)

    def update_trainer(self, trainer_id, full_name, phone, specialization, monthly_salary, hire_date):
        if not self.get_trainer_by_id(trainer_id):
            raise ValueError(f"Trainer with ID {trainer_id} not found.")
        v = validate_trainer_fields(full_name, phone, specialization, monthly_salary, hire_date)
        self._execute(
            "UPDATE trainers SET full_name = %s, phone = %s, specialization = %s, "
            "monthly_salary = %s, hire_date = %s WHERE trainer_id = %s",
            (v["full_name"], v["phone"], v["specialization"], v["monthly_salary"], v["hire_date"], trainer_id),
        )
        return self.get_trainer_by_id(trainer_id)

    def delete_trainer(self, trainer_id):
        """FK fk_members_trainer is ON DELETE SET NULL: assigned members become unassigned."""
        if not self.get_trainer_by_id(trainer_id):
            raise ValueError(f"Trainer with ID {trainer_id} not found.")
        reassigned = self._scalar("SELECT COUNT(*) FROM members WHERE trainer_id = %s", (trainer_id,))
        self._execute("DELETE FROM trainers WHERE trainer_id = %s", (trainer_id,))
        return int(reassigned or 0)

    # -------------------------------------------------------------
    # Packages
    # -------------------------------------------------------------
    def get_all_packages(self):
        rows = self._query("""
            SELECT p.package_id, p.package_name, p.duration_days, p.fee, p.description,
                   COALESCE(SUM(s.end_date >= CURDATE()), 0) AS active_subscribers,
                   COUNT(s.sub_id)                            AS total_subscriptions
            FROM packages p
            LEFT JOIN subscriptions s ON s.package_id = p.package_id
            GROUP BY p.package_id, p.package_name, p.duration_days, p.fee, p.description
            ORDER BY p.package_id
        """)
        for r in rows:
            r["active_subscribers"] = int(r["active_subscribers"])
            r["total_subscriptions"] = int(r["total_subscriptions"])
            r["description"] = r["description"] or ""
        return rows

    def get_package_by_id(self, package_id):
        row = self._query_one("SELECT * FROM packages WHERE package_id = %s", (package_id,))
        if row:
            row["description"] = row["description"] or ""
        return row

    def add_package(self, package_name, duration_days, fee, description):
        v = validate_package_fields(package_name, duration_days, fee, description)
        new_id, _ = self._execute(
            "INSERT INTO packages (package_name, duration_days, fee, description) VALUES (%s, %s, %s, %s)",
            (v["package_name"], v["duration_days"], v["fee"], v["description"]),
        )
        return self.get_package_by_id(new_id)

    def update_package(self, package_id, package_name, duration_days, fee, description):
        if not self.get_package_by_id(package_id):
            raise ValueError(f"Package ID {package_id} not found.")
        v = validate_package_fields(package_name, duration_days, fee, description)
        self._execute(
            "UPDATE packages SET package_name = %s, duration_days = %s, fee = %s, description = %s "
            "WHERE package_id = %s",
            (v["package_name"], v["duration_days"], v["fee"], v["description"], package_id),
        )
        return self.get_package_by_id(package_id)

    def delete_package(self, package_id):
        """FK fk_subscriptions_package is ON DELETE RESTRICT."""
        pkg = self.get_package_by_id(package_id)
        if not pkg:
            raise ValueError(f"Package ID {package_id} not found.")
        refs = self._scalar("SELECT COUNT(*) FROM subscriptions WHERE package_id = %s", (package_id,))
        if refs:
            raise ValueError(
                f"Referential Integrity Restriction (ON DELETE RESTRICT): "
                f"Cannot delete package '{pkg['package_name']}' because {refs} "
                f"subscription record(s) reference it."
            )
        self._execute("DELETE FROM packages WHERE package_id = %s", (package_id,))
        return True

    # -------------------------------------------------------------
    # Members
    # -------------------------------------------------------------
    @staticmethod
    def _normalise_member(row):
        row["emergency_contact_name"] = row.get("emergency_contact_name") or ""
        row["emergency_contact_phone"] = row.get("emergency_contact_phone") or ""
        return row

    def get_all_members_detailed(self):
        rows = self._query("SELECT * FROM v_member_overview ORDER BY member_id")
        for r in rows:
            self._normalise_member(r)
            r["sub_start"] = r["sub_start"] or "-"
            r["sub_end"] = r["sub_end"] or "-"
            r["payment_method"] = r["payment_method"] or "-"
        return rows

    def get_member_by_id(self, member_id):
        row = self._query_one("SELECT * FROM members WHERE member_id = %s", (member_id,))
        return self._normalise_member(row) if row else None

    def add_member(self, full_name, phone, email, gender, join_date, trainer_id=None,
                   emergency_contact_name="", emergency_contact_phone=""):
        v = validate_member_fields(full_name, phone, email, gender, join_date,
                                   emergency_contact_name, emergency_contact_phone)
        new_id, _ = self._execute(
            "INSERT INTO members (full_name, phone, email, gender, join_date, "
            "emergency_contact_name, emergency_contact_phone, trainer_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (v["full_name"], v["phone"], v["email"], v["gender"], v["join_date"],
             v["emergency_contact_name"] or None, v["emergency_contact_phone"] or None,
             int(trainer_id) if trainer_id else None),
        )
        return self.get_member_by_id(new_id)

    def update_member(self, member_id, full_name, phone, email, gender, join_date, trainer_id=None,
                      emergency_contact_name="", emergency_contact_phone=""):
        if not self.get_member_by_id(member_id):
            raise ValueError(f"Member ID {member_id} not found.")
        v = validate_member_fields(full_name, phone, email, gender, join_date,
                                   emergency_contact_name, emergency_contact_phone)
        self._execute(
            "UPDATE members SET full_name = %s, phone = %s, email = %s, gender = %s, join_date = %s, "
            "emergency_contact_name = %s, emergency_contact_phone = %s, trainer_id = %s "
            "WHERE member_id = %s",
            (v["full_name"], v["phone"], v["email"], v["gender"], v["join_date"],
             v["emergency_contact_name"] or None, v["emergency_contact_phone"] or None,
             int(trainer_id) if trainer_id else None, member_id),
        )
        return self.get_member_by_id(member_id)

    def delete_member(self, member_id):
        """FK fk_subscriptions_member is ON DELETE CASCADE: the member's ledger rows go too."""
        if not self.get_member_by_id(member_id):
            raise ValueError(f"Member ID {member_id} not found.")
        cascaded = self._scalar("SELECT COUNT(*) FROM subscriptions WHERE member_id = %s", (member_id,))
        self._execute("DELETE FROM members WHERE member_id = %s", (member_id,))
        return int(cascaded or 0)

    # -------------------------------------------------------------
    # Subscriptions & Billing
    # -------------------------------------------------------------
    def get_all_subscriptions_detailed(self):
        return self._query("""
            SELECT s.sub_id, s.member_id, s.package_id, s.payment_date, s.start_date, s.end_date,
                   s.amount_paid, s.payment_method,
                   m.full_name     AS member_name,
                   m.phone         AS member_phone,
                   p.package_name,
                   p.duration_days,
                   DATEDIFF(s.end_date, CURDATE()) AS days_left,
                   """ + STATUS_CASE + """ AS status
            FROM subscriptions s
            INNER JOIN members  m ON m.member_id  = s.member_id
            INNER JOIN packages p ON p.package_id = s.package_id
            ORDER BY s.end_date DESC, s.sub_id DESC
        """)

    def get_renewal_start_date(self, member_id):
        """Renewals continue from the current plan's end date; lapsed members start today."""
        return self._scalar(
            "SELECT GREATEST(CURDATE(), COALESCE(MAX(end_date), CURDATE())) "
            "FROM subscriptions WHERE member_id = %s",
            (member_id,),
        )

    def add_subscription(self, member_id, package_id, start_date_str, amount_paid, payment_method):
        """Insert a payment; end_date is computed by the database with DATE_ADD()."""
        start = validate_date(start_date_str, "Start date")
        amount, method = validate_payment(amount_paid, payment_method)
        if not self.get_member_by_id(member_id):
            raise ValueError(f"Member ID {member_id} does not exist.")
        new_id, rowcount = self._execute(
            "INSERT INTO subscriptions "
            "(member_id, package_id, payment_date, start_date, end_date, amount_paid, payment_method) "
            "SELECT %s, p.package_id, CURDATE(), %s, DATE_ADD(%s, INTERVAL p.duration_days DAY), %s, %s "
            "FROM packages p WHERE p.package_id = %s",
            (int(member_id), start, start, amount, method, int(package_id)),
        )
        if not rowcount:
            raise ValueError(f"Package ID {package_id} does not exist.")
        return self._query_one("SELECT * FROM subscriptions WHERE sub_id = %s", (new_id,))

    def delete_subscription(self, sub_id):
        _, rowcount = self._execute("DELETE FROM subscriptions WHERE sub_id = %s", (sub_id,))
        return rowcount > 0

    # -------------------------------------------------------------
    # Member profile & history
    # -------------------------------------------------------------
    def get_member_profile(self, member_id):
        """Member overview + full payment history + lifetime totals."""
        member = self._query_one("SELECT * FROM v_member_overview WHERE member_id = %s", (member_id,))
        if not member:
            return None
        self._normalise_member(member)
        payments = self._query("""
            SELECT s.sub_id, s.payment_date, s.start_date, s.end_date, s.amount_paid, s.payment_method,
                   p.package_name, p.duration_days,
                   DATEDIFF(s.end_date, CURDATE()) AS days_left,
                   """ + STATUS_CASE + """ AS status
            FROM subscriptions s
            INNER JOIN packages p ON p.package_id = s.package_id
            WHERE s.member_id = %s
            ORDER BY s.end_date DESC, s.sub_id DESC
        """, (member_id,))
        stats = self._query_one("""
            SELECT COUNT(*)                     AS payments,
                   COALESCE(SUM(amount_paid), 0) AS total_spent,
                   MIN(payment_date)            AS first_payment,
                   MAX(payment_date)            AS last_payment,
                   COALESCE(SUM(DATEDIFF(end_date, start_date)), 0) AS days_purchased
            FROM subscriptions WHERE member_id = %s
        """, (member_id,))
        stats["payments"] = int(stats["payments"])
        stats["days_purchased"] = int(stats["days_purchased"])
        return {"member": member, "payments": payments, "stats": stats}

    # -------------------------------------------------------------
    # Audit log (filled by triggers)
    # -------------------------------------------------------------
    def get_audit_log(self, limit=500):
        return self._query(
            "SELECT log_id, event_time, app_user, action, table_name, record_id, details "
            "FROM audit_log ORDER BY log_id DESC LIMIT %s",
            (int(limit),),
        )

    # -------------------------------------------------------------
    # Analytics (aggregate SQL)
    # -------------------------------------------------------------
    def get_monthly_revenue(self, months=6):
        rows = self._query(
            "SELECT DATE_FORMAT(payment_date, '%Y-%m') AS month, "
            "       SUM(amount_paid) AS total, COUNT(*) AS payments "
            "FROM subscriptions "
            f"WHERE payment_date >= DATE_SUB(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL {int(months) - 1} MONTH) "
            "GROUP BY month ORDER BY month"
        )
        by_month = {r["month"]: r for r in rows}
        return [
            {"month": key,
             "total": float(by_month.get(key, {}).get("total", 0.0)),
             "payments": int(by_month.get(key, {}).get("payments", 0))}
            for key in last_n_months(months)
        ]

    def get_dashboard_metrics(self):
        totals = self._query_one("""
            SELECT (SELECT COALESCE(SUM(amount_paid), 0) FROM subscriptions) AS total_revenue,
                   (SELECT COUNT(*) FROM members)  AS total_members,
                   (SELECT COUNT(*) FROM trainers) AS total_trainers,
                   (SELECT COUNT(*) FROM packages) AS total_packages
        """)

        status_counts = {"Active": 0, "Expiring Soon": 0, "Expired": 0, "No Subscription": 0}
        for r in self._query("SELECT status, COUNT(*) AS n FROM v_member_overview GROUP BY status"):
            status_counts[r["status"]] = int(r["n"])

        revenue_by_method = {
            r["payment_method"]: float(r["total"])
            for r in self._query(
                "SELECT payment_method, SUM(amount_paid) AS total FROM subscriptions "
                "GROUP BY payment_method HAVING SUM(amount_paid) > 0 ORDER BY total DESC"
            )
        }

        expiring = self._query(
            "SELECT * FROM v_member_overview WHERE status = 'Expiring Soon' ORDER BY days_left, full_name"
        )

        return {
            "total_revenue": float(totals["total_revenue"]),
            "total_members": int(totals["total_members"]),
            "total_trainers": int(totals["total_trainers"]),
            "total_packages": int(totals["total_packages"]),
            "status_counts": status_counts,
            "revenue_by_method": revenue_by_method,
            "monthly_revenue": self.get_monthly_revenue(6),
            "expiring_soon_list": expiring,
            "trainers_workload": self.get_all_trainers(),
        }
