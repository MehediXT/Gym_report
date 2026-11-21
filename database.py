"""
JSON-persisted fallback data store.

Used when the MySQL server is not reachable (or when GYM_DB_BACKEND=json).
It mirrors the MySQL backend's public interface and imitates the same rules
in Python: UNIQUE/CHECK validation, ON DELETE CASCADE / SET NULL / RESTRICT,
DATE_ADD-style end dates and aggregate reports.
"""

import os
import json
from datetime import date, datetime, timedelta

from common import (
    hash_password, validate_member_fields, validate_trainer_fields,
    validate_package_fields, validate_payment, validate_date,
    compute_subscription_status, calculate_end_date, last_n_months,
)

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gym_data.json")


def _d(days):
    """Date string relative to today (negative = past)."""
    return (date.today() + timedelta(days=days)).strftime("%Y-%m-%d")


class GymDatabase:
    backend_name = "JSON"

    def __init__(self, filepath=DATA_FILE):
        self.filepath = filepath
        self.backend_label = f"JSON file · {os.path.basename(filepath)}"
        self.app_user = None
        self.triggers_enabled = False  # the log is written by Python, not database triggers
        self.data = {"users": [], "trainers": [], "packages": [], "members": [], "subscriptions": [], "audit_log": []}
        self.load()

    compute_subscription_status = staticmethod(compute_subscription_status)
    calculate_end_date = staticmethod(calculate_end_date)

    # -------------------------------------------------------------
    # Persistence & Initialization
    # -------------------------------------------------------------
    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                self._migrate()
                return
            except Exception as e:
                print(f"Error loading {self.filepath}: {e}. Initializing seed data.")
        self.reset_to_demo_data()

    def _migrate(self):
        """Add fields introduced after older versions of gym_data.json were written."""
        changed = False
        if "audit_log" not in self.data:
            self.data["audit_log"] = []
            changed = True
        for m in self.data.get("members", []):
            for key in ("emergency_contact_name", "emergency_contact_phone"):
                if key not in m:
                    m[key] = ""
                    changed = True
        for s in self.data.get("subscriptions", []):
            if "payment_date" not in s:
                s["payment_date"] = s["start_date"]
                changed = True
        if changed:
            self.save()

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Failed to save data: {e}")

    def reset_to_demo_data(self):
        """Same demo data as sql/seed.sql, with dates relative to today."""
        users = [
            {"user_id": 1, "username": "admin", "password_hash": hash_password("admin123"),
             "role": "Admin", "full_name": "Marcus Vance (Administrator)"},
            {"user_id": 2, "username": "staff", "password_hash": hash_password("staff123"),
             "role": "Staff", "full_name": "Elena Rostova (Desk Staff)"},
            {"user_id": 3, "username": "manager", "password_hash": hash_password("manager123"),
             "role": "Manager", "full_name": "David Sterling (Operations Mgr)"},
        ]
        trainers = [
            {"trainer_id": tid, "full_name": n, "phone": p, "specialization": s,
             "monthly_salary": sal, "hire_date": h}
            for tid, n, p, s, sal, h in [
                (101, "Alex 'Titan' Rivera", "+1-555-0192", "Strength & Bodybuilding", 4500.0, "2023-01-15"),
                (102, "Sarah Jenkins", "+1-555-0144", "HIIT & Cardio Conditioning", 4200.0, "2023-03-20"),
                (103, "Liam Chen", "+1-555-0188", "CrossFit & Mobility", 4400.0, "2023-06-10"),
                (104, "Priya Sharma", "+1-555-0131", "Yoga & Pilates", 3900.0, "2023-08-01"),
                (105, "Marcus Brody", "+1-555-0177", "Athletic Rehab & Powerlifting", 4800.0, "2022-11-05"),
            ]
        ]
        packages = [
            {"package_id": pid, "package_name": n, "duration_days": d, "fee": fee, "description": desc}
            for pid, n, d, fee, desc in [
                (1, "Monthly Starter", 30, 59.99, "Standard 30-day gym floor access with basic cardio and weights."),
                (2, "Quarterly Pro", 90, 159.99, "90-day all-access membership including locker room and steam bath."),
                (3, "Semi-Annual Elite", 180, 289.99, "6 months full access with complimentary nutrition consultation."),
                (4, "Annual VIP Champion", 365, 499.99, "365 days unlimited 24/7 access, VIP lounge, guest passes, and towel service."),
                (5, "Student Flex 30", 30, 39.99, "Discounted 30-day access for active students with valid ID."),
            ]
        ]
        members = [
            {"member_id": mid, "full_name": n, "phone": p, "email": e, "gender": g, "join_date": j,
             "emergency_contact_name": ecn, "emergency_contact_phone": ecp, "trainer_id": t}
            for mid, n, p, e, g, j, ecn, ecp, t in [
                (1001, "Johnathan Miller", "+1-555-1101", "j.miller@example.com", "Male", "2024-01-10", "Laura Miller", "+1-555-2101", 101),
                (1002, "Emily Watson", "+1-555-1102", "emily.w@example.com", "Female", "2024-02-15", "Mark Watson", "+1-555-2102", 102),
                (1003, "Michael Chang", "+1-555-1103", "mchang@example.com", "Male", "2024-03-01", "Grace Chang", "+1-555-2103", 103),
                (1004, "Sophia Rodriguez", "+1-555-1104", "sophia.r@example.com", "Female", "2024-04-12", "Carlos Rodriguez", "+1-555-2104", 104),
                (1005, "David Kim", "+1-555-1105", "dkim@example.com", "Male", "2024-05-20", "Min-ji Kim", "+1-555-2105", 101),
                (1006, "Chloe Bennett", "+1-555-1106", "chloe.b@example.com", "Female", "2024-06-18", "Oliver Bennett", "+1-555-2106", 102),
                (1007, "Robert Downey", "+1-555-1107", "rdowney@example.com", "Male", "2024-07-04", "", "", None),
                (1008, "Amina Al-Mansoor", "+1-555-1108", "amina.m@example.com", "Female", "2024-08-11", "Yusuf Al-Mansoor", "+1-555-2108", 104),
                (1009, "Lucas Silva", "+1-555-1109", "lucas.s@example.com", "Male", "2024-09-02", "Ana Silva", "+1-555-2109", 105),
                (1010, "Grace Hopper", "+1-555-1110", "grace.h@example.com", "Female", "2024-09-25", "", "", None),
            ]
        ]
        # (sub_id, member_id, package_id, start offset, end offset, amount, method)
        subs = [
            (5001, 1004, 1, -135, -105, 59.99, "Cash"),
            (5002, 1006, 2, -160, -70, 159.99, "Credit Card"),
            (5003, 1005, 1, -100, -70, 59.99, "UPI / Digital"),
            (5004, 1003, 1, -118, -88, 59.99, "Debit Card"),
            (5005, 1001, 4, -60, 305, 499.99, "Credit Card"),
            (5006, 1002, 1, -26, 4, 59.99, "Debit Card"),
            (5007, 1003, 2, -88, 2, 159.99, "Cash"),
            (5008, 1004, 2, -45, 45, 159.99, "Bank Transfer"),
            (5009, 1005, 1, -40, -10, 59.99, "Cash"),
            (5010, 1006, 3, -70, 110, 289.99, "Credit Card"),
            (5011, 1007, 5, -55, -25, 39.99, "Credit Card"),
            (5012, 1008, 1, -12, 18, 59.99, "UPI / Digital"),
            (5013, 1009, 1, -24, 6, 59.99, "Debit Card"),
            (5014, 1010, 4, -115, 250, 499.99, "Bank Transfer"),
        ]
        subscriptions = [
            {"sub_id": sid, "member_id": mid, "package_id": pid, "payment_date": _d(start),
             "start_date": _d(start), "end_date": _d(end), "amount_paid": amt, "payment_method": meth}
            for sid, mid, pid, start, end, amt, meth in subs
        ]
        self.data = {"users": users, "trainers": trainers, "packages": packages,
                     "members": members, "subscriptions": subscriptions, "audit_log": []}
        self._log("DEMO_RESET", "all", None,
                  "Demo data restored with the Reset button" if self.app_user else "Demo data loaded")
        self.save()

    # -------------------------------------------------------------
    # Audit log (Python equivalent of sql/triggers.sql)
    # -------------------------------------------------------------
    def set_session_user(self, username):
        self.app_user = username

    def _log(self, action, table_name, record_id, details):
        log = self.data.setdefault("audit_log", [])
        log.append({
            "log_id": max([e["log_id"] for e in log] + [0]) + 1,
            "event_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "app_user": self.app_user or "system",
            "action": action, "table_name": table_name, "record_id": record_id, "details": details,
        })

    def get_audit_log(self, limit=500):
        return sorted(self.data.get("audit_log", []), key=lambda e: e["log_id"], reverse=True)[:limit]

    # -------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------
    def authenticate(self, username, password):
        h = hash_password(password)
        for u in self.data["users"]:
            if u["username"].lower() == username.strip().lower() and u["password_hash"] == h:
                return {"user_id": u["user_id"], "username": u["username"], "role": u["role"],
                        "full_name": u.get("full_name", u["username"])}
        return None

    # -------------------------------------------------------------
    # Trainers
    # -------------------------------------------------------------
    def get_all_trainers(self):
        status_by_member = {m["member_id"]: m["status"] for m in self.get_all_members_detailed()}
        trainers = []
        for t in self.data["trainers"]:
            t_copy = dict(t)
            assigned = sorted(
                (m for m in self.data["members"] if m.get("trainer_id") == t["trainer_id"]),
                key=lambda m: m["full_name"],
            )
            t_copy["assigned_count"] = len(assigned)
            t_copy["active_count"] = sum(
                1 for m in assigned if status_by_member.get(m["member_id"]) in ("Active", "Expiring Soon")
            )
            t_copy["assigned_members"] = [m["full_name"] for m in assigned]
            trainers.append(t_copy)
        return trainers

    def get_trainer_by_id(self, trainer_id):
        return next((t for t in self.data["trainers"] if t["trainer_id"] == trainer_id), None)

    def add_trainer(self, full_name, phone, specialization, monthly_salary, hire_date):
        v = validate_trainer_fields(full_name, phone, specialization, monthly_salary, hire_date)
        if any(t["phone"] == v["phone"] for t in self.data["trainers"]):
            raise ValueError("Constraint Violation (UNIQUE): This phone number is already used by another trainer.")
        new_id = max([t["trainer_id"] for t in self.data["trainers"]] + [100]) + 1
        trainer = {"trainer_id": new_id, **v}
        self.data["trainers"].append(trainer)
        self.save()
        return trainer

    def update_trainer(self, trainer_id, full_name, phone, specialization, monthly_salary, hire_date):
        trainer = self.get_trainer_by_id(trainer_id)
        if not trainer:
            raise ValueError(f"Trainer with ID {trainer_id} not found.")
        v = validate_trainer_fields(full_name, phone, specialization, monthly_salary, hire_date)
        if any(t["phone"] == v["phone"] and t["trainer_id"] != trainer_id for t in self.data["trainers"]):
            raise ValueError("Constraint Violation (UNIQUE): This phone number is already used by another trainer.")
        trainer.update(v)
        self.save()
        return trainer

    def delete_trainer(self, trainer_id):
        """ON DELETE SET NULL for members assigned to this trainer."""
        trainer = self.get_trainer_by_id(trainer_id)
        if not trainer:
            raise ValueError(f"Trainer with ID {trainer_id} not found.")
        self._log("TRAINER_DELETED", "trainers", trainer_id,
                  f"Removed trainer {trainer['full_name']} ({trainer['specialization']})")
        reassigned = 0
        for m in self.data["members"]:
            if m.get("trainer_id") == trainer_id:
                m["trainer_id"] = None
                reassigned += 1
        self.data["trainers"] = [t for t in self.data["trainers"] if t["trainer_id"] != trainer_id]
        self.save()
        return reassigned

    # -------------------------------------------------------------
    # Packages
    # -------------------------------------------------------------
    def get_all_packages(self):
        today = date.today().strftime("%Y-%m-%d")
        packages = []
        for p in self.data["packages"]:
            p_copy = dict(p)
            subs = [s for s in self.data["subscriptions"] if s["package_id"] == p["package_id"]]
            p_copy["active_subscribers"] = sum(1 for s in subs if s["end_date"] >= today)
            p_copy["total_subscriptions"] = len(subs)
            packages.append(p_copy)
        return packages

    def get_package_by_id(self, package_id):
        return next((p for p in self.data["packages"] if p["package_id"] == package_id), None)

    def _check_package_name(self, name, exclude_id=None):
        if any(p["package_name"].lower() == name.lower() and p["package_id"] != exclude_id
               for p in self.data["packages"]):
            raise ValueError("Constraint Violation (UNIQUE): A package with this name already exists.")

    def add_package(self, package_name, duration_days, fee, description):
        v = validate_package_fields(package_name, duration_days, fee, description)
        self._check_package_name(v["package_name"])
        new_id = max([p["package_id"] for p in self.data["packages"]] + [0]) + 1
        package = {"package_id": new_id, **v}
        self.data["packages"].append(package)
        self.save()
        return package

    def update_package(self, package_id, package_name, duration_days, fee, description):
        pkg = self.get_package_by_id(package_id)
        if not pkg:
            raise ValueError(f"Package ID {package_id} not found.")
        v = validate_package_fields(package_name, duration_days, fee, description)
        self._check_package_name(v["package_name"], exclude_id=package_id)
        if float(pkg["fee"]) != v["fee"]:
            self._log("PRICE_CHANGED", "packages", package_id,
                      f"{v['package_name']} fee ${float(pkg['fee']):.2f} -> ${v['fee']:.2f}")
        pkg.update(v)
        self.save()
        return pkg

    def delete_package(self, package_id):
        """ON DELETE RESTRICT: refuse while subscriptions reference the package."""
        pkg = self.get_package_by_id(package_id)
        if not pkg:
            raise ValueError(f"Package ID {package_id} not found.")
        refs = sum(1 for s in self.data["subscriptions"] if s["package_id"] == package_id)
        if refs:
            raise ValueError(
                f"Referential Integrity Restriction (ON DELETE RESTRICT): "
                f"Cannot delete package '{pkg['package_name']}' because {refs} "
                f"subscription record(s) reference it."
            )
        self.data["packages"] = [p for p in self.data["packages"] if p["package_id"] != package_id]
        self.save()
        return True

    # -------------------------------------------------------------
    # Members
    # -------------------------------------------------------------
    def _latest_subscription(self, member_id):
        subs = [s for s in self.data["subscriptions"] if s["member_id"] == member_id]
        return max(subs, key=lambda s: (s["end_date"], s["sub_id"])) if subs else None

    def get_all_members_detailed(self):
        """Python version of the v_member_overview view (LEFT JOINs + latest plan)."""
        trainers_map = {t["trainer_id"]: t["full_name"] for t in self.data["trainers"]}
        packages_map = {p["package_id"]: p for p in self.data["packages"]}
        results = []
        for m in self.data["members"]:
            row = dict(m)
            row["trainer_name"] = trainers_map.get(m.get("trainer_id"), "Unassigned")
            latest = self._latest_subscription(m["member_id"])
            if latest:
                status, days_left = compute_subscription_status(latest["end_date"])
                row.update({
                    "latest_sub_id": latest["sub_id"],
                    "package_name": packages_map.get(latest["package_id"], {}).get("package_name", "Unknown Package"),
                    "sub_start": latest["start_date"], "sub_end": latest["end_date"],
                    "amount_paid": latest["amount_paid"], "payment_method": latest["payment_method"],
                    "status": status, "days_left": days_left,
                })
            else:
                row.update({
                    "latest_sub_id": None, "package_name": "No Subscription",
                    "sub_start": "-", "sub_end": "-", "amount_paid": 0.0, "payment_method": "-",
                    "status": "No Subscription", "days_left": None,
                })
            results.append(row)
        return results

    def get_member_by_id(self, member_id):
        return next((m for m in self.data["members"] if m["member_id"] == member_id), None)

    def _check_member_phone(self, phone, exclude_id=None):
        if any(m["phone"] == phone and m["member_id"] != exclude_id for m in self.data["members"]):
            raise ValueError("Constraint Violation (UNIQUE): This phone number is already used by another member.")

    def _check_trainer_fk(self, trainer_id):
        if trainer_id and not self.get_trainer_by_id(int(trainer_id)):
            raise ValueError(f"Referential Integrity Violation (FOREIGN KEY): trainer {trainer_id} does not exist.")

    def add_member(self, full_name, phone, email, gender, join_date, trainer_id=None,
                   emergency_contact_name="", emergency_contact_phone=""):
        v = validate_member_fields(full_name, phone, email, gender, join_date,
                                   emergency_contact_name, emergency_contact_phone)
        self._check_member_phone(v["phone"])
        self._check_trainer_fk(trainer_id)
        new_id = max([m["member_id"] for m in self.data["members"]] + [1000]) + 1
        member = {"member_id": new_id, **v, "trainer_id": int(trainer_id) if trainer_id else None}
        self.data["members"].append(member)
        self._log("MEMBER_ADDED", "members", new_id, f"Registered {v['full_name']} ({v['phone']})")
        self.save()
        return member

    def update_member(self, member_id, full_name, phone, email, gender, join_date, trainer_id=None,
                      emergency_contact_name="", emergency_contact_phone=""):
        member = self.get_member_by_id(member_id)
        if not member:
            raise ValueError(f"Member ID {member_id} not found.")
        v = validate_member_fields(full_name, phone, email, gender, join_date,
                                   emergency_contact_name, emergency_contact_phone)
        self._check_member_phone(v["phone"], exclude_id=member_id)
        self._check_trainer_fk(trainer_id)
        new_trainer = int(trainer_id) if trainer_id else None
        details = f"Updated {v['full_name']}"
        if member.get("trainer_id") != new_trainer:
            details += " (trainer changed)"
        if member["phone"] != v["phone"]:
            details += f" (phone {member['phone']} -> {v['phone']})"
        self._log("MEMBER_UPDATED", "members", member_id, details)
        member.update(v)
        member["trainer_id"] = new_trainer
        self.save()
        return member

    def delete_member(self, member_id):
        """ON DELETE CASCADE: remove the member's subscriptions as well."""
        member = self.get_member_by_id(member_id)
        if not member:
            raise ValueError(f"Member ID {member_id} not found.")
        self._log("MEMBER_DELETED", "members", member_id,
                  f"Deleted {member['full_name']} ({member['phone']}) and their payment history")
        before = len(self.data["subscriptions"])
        self.data["subscriptions"] = [s for s in self.data["subscriptions"] if s["member_id"] != member_id]
        cascaded = before - len(self.data["subscriptions"])
        self.data["members"] = [m for m in self.data["members"] if m["member_id"] != member_id]
        self.save()
        return cascaded

    # -------------------------------------------------------------
    # Subscriptions & Billing
    # -------------------------------------------------------------
    def get_all_subscriptions_detailed(self):
        members_map = {m["member_id"]: m for m in self.data["members"]}
        packages_map = {p["package_id"]: p for p in self.data["packages"]}
        results = []
        for s in self.data["subscriptions"]:
            row = dict(s)
            mem = members_map.get(s["member_id"], {})
            pkg = packages_map.get(s["package_id"], {})
            row["member_name"] = mem.get("full_name", f"Member #{s['member_id']}")
            row["member_phone"] = mem.get("phone", "")
            row["package_name"] = pkg.get("package_name", f"Package #{s['package_id']}")
            row["duration_days"] = pkg.get("duration_days", 30)
            row["status"], row["days_left"] = compute_subscription_status(s["end_date"])
            results.append(row)
        return sorted(results, key=lambda x: (x["end_date"], x["sub_id"]), reverse=True)

    def get_renewal_start_date(self, member_id):
        """Renewals continue from the current plan's end date; lapsed members start today."""
        today = date.today().strftime("%Y-%m-%d")
        latest = self._latest_subscription(member_id)
        return max(today, latest["end_date"]) if latest else today

    def add_subscription(self, member_id, package_id, start_date_str, amount_paid, payment_method):
        start = validate_date(start_date_str, "Start date")
        amount, method = validate_payment(amount_paid, payment_method)
        if not self.get_member_by_id(member_id):
            raise ValueError(f"Member ID {member_id} does not exist.")
        package = self.get_package_by_id(package_id)
        if not package:
            raise ValueError(f"Package ID {package_id} does not exist.")
        new_id = max([s["sub_id"] for s in self.data["subscriptions"]] + [5000]) + 1
        sub = {
            "sub_id": new_id, "member_id": int(member_id), "package_id": int(package_id),
            "payment_date": date.today().strftime("%Y-%m-%d"),
            "start_date": start, "end_date": calculate_end_date(start, package["duration_days"]),
            "amount_paid": amount, "payment_method": method,
        }
        self.data["subscriptions"].append(sub)
        self._log("PAYMENT_RECORDED", "subscriptions", new_id,
                  f"{self.get_member_by_id(int(member_id))['full_name']} paid ${amount:.2f} ({method}) for "
                  f"{package['package_name']}, valid {start} to {sub['end_date']}")
        self.save()
        return sub

    def delete_subscription(self, sub_id):
        sub = next((s for s in self.data["subscriptions"] if s["sub_id"] == sub_id), None)
        if sub:
            mem = self.get_member_by_id(sub["member_id"]) or {}
            self._log("PAYMENT_VOIDED", "subscriptions", sub_id,
                      f"Voided ${sub['amount_paid']:.2f} payment of {mem.get('full_name', 'member #%s' % sub['member_id'])} "
                      f"({sub['start_date']} to {sub['end_date']})")
        before = len(self.data["subscriptions"])
        self.data["subscriptions"] = [s for s in self.data["subscriptions"] if s["sub_id"] != sub_id]
        if len(self.data["subscriptions"]) < before:
            self.save()
            return True
        return False

    # -------------------------------------------------------------
    # Member profile & history
    # -------------------------------------------------------------
    def get_member_profile(self, member_id):
        member = next((m for m in self.get_all_members_detailed() if m["member_id"] == member_id), None)
        if not member:
            return None
        packages_map = {p["package_id"]: p for p in self.data["packages"]}
        payments = []
        for s in self.data["subscriptions"]:
            if s["member_id"] != member_id:
                continue
            row = dict(s)
            pkg = packages_map.get(s["package_id"], {})
            row["package_name"] = pkg.get("package_name", f"Package #{s['package_id']}")
            row["duration_days"] = pkg.get("duration_days")
            row["status"], row["days_left"] = compute_subscription_status(s["end_date"])
            payments.append(row)
        payments.sort(key=lambda r: (r["end_date"], r["sub_id"]), reverse=True)
        paid_on = [p.get("payment_date", p["start_date"]) for p in payments]
        stats = {
            "payments": len(payments),
            "total_spent": sum(p["amount_paid"] for p in payments),
            "first_payment": min(paid_on) if paid_on else None,
            "last_payment": max(paid_on) if paid_on else None,
            "days_purchased": sum((datetime.strptime(p["end_date"], "%Y-%m-%d") -
                                   datetime.strptime(p["start_date"], "%Y-%m-%d")).days for p in payments),
        }
        return {"member": member, "payments": payments, "stats": stats}

    # -------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------
    def get_monthly_revenue(self, months=6):
        keys = last_n_months(months)
        totals = {k: {"month": k, "total": 0.0, "payments": 0} for k in keys}
        for s in self.data["subscriptions"]:
            key = s.get("payment_date", s["start_date"])[:7]
            if key in totals:
                totals[key]["total"] += s["amount_paid"]
                totals[key]["payments"] += 1
        return [totals[k] for k in keys]

    def get_dashboard_metrics(self):
        members = self.get_all_members_detailed()
        status_counts = {"Active": 0, "Expiring Soon": 0, "Expired": 0, "No Subscription": 0}
        for m in members:
            status_counts[m["status"]] = status_counts.get(m["status"], 0) + 1

        revenue_by_method = {}
        for s in self.data["subscriptions"]:
            revenue_by_method[s["payment_method"]] = revenue_by_method.get(s["payment_method"], 0.0) + s["amount_paid"]

        expiring = sorted((m for m in members if m["status"] == "Expiring Soon"),
                          key=lambda m: (m["days_left"], m["full_name"]))

        return {
            "total_revenue": sum(s["amount_paid"] for s in self.data["subscriptions"]),
            "total_members": len(members),
            "total_trainers": len(self.data["trainers"]),
            "total_packages": len(self.data["packages"]),
            "status_counts": status_counts,
            "revenue_by_method": dict(sorted(revenue_by_method.items(), key=lambda x: x[1], reverse=True)),
            "monthly_revenue": self.get_monthly_revenue(6),
            "expiring_soon_list": expiring,
            "trainers_workload": self.get_all_trainers(),
        }
