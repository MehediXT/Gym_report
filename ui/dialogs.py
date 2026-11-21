"""
Modal dialogs: member / trainer / plan / payment forms plus confirm and message boxes.
All share BaseModal's layout: header, form body, footer action bar.
"""

import customtkinter as ctk
from datetime import date, datetime
from ui.theme import (
    COLORS, STATUS_COLORS, F, button, entry, combo, field_label, card, table,
    insert_row, style_tree_tags, status_text, setup_treeview_style,
)
from common import PAYMENT_METHODS, GENDERS

SPECIALIZATIONS = [
    "Strength & Bodybuilding",
    "HIIT & Cardio Conditioning",
    "CrossFit & Mobility",
    "Yoga & Pilates",
    "Athletic Rehab & Powerlifting",
    "Boxing & Martial Arts",
]


class BaseModal(ctk.CTkToplevel):
    """Centered, modal window with a consistent header / body / footer layout."""

    def __init__(self, parent, title="Dialog", width=500, height=520, subtitle=None, scroll=True):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=COLORS["surface"])
        self.result = None

        self.transient(parent)
        pos_x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        pos_y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{max(0, pos_x)}+{max(0, pos_y)}")

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 4))
        ctk.CTkLabel(header, text=title, font=F(20, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(header, text=subtitle, font=F(12), text_color=COLORS["text_muted"],
                         wraplength=width - 60, justify="left").pack(anchor="w", pady=(2, 0))

        # Footer (packed before the body so it always stays visible)
        footer_wrap = ctk.CTkFrame(self, fg_color=COLORS["surface_alt"], corner_radius=0)
        footer_wrap.pack(side="bottom", fill="x")
        ctk.CTkFrame(footer_wrap, height=1, corner_radius=0, fg_color=COLORS["border"]).pack(fill="x")
        self.footer = ctk.CTkFrame(footer_wrap, fg_color="transparent")
        self.footer.pack(fill="x", padx=28, pady=14)

        # Body
        if scroll:
            self.body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                               scrollbar_button_color=COLORS["border"])
        else:
            self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=(22, 16), pady=(8, 8))

        self.grab_set()
        self.focus_set()

    # --- form helpers -------------------------------------------------
    def error_label(self):
        lbl = ctk.CTkLabel(self.body, text="", text_color=COLORS["danger"], font=F(12, "bold"),
                           wraplength=440, justify="left", anchor="w")
        lbl.pack(anchor="w", fill="x", padx=6)
        return lbl

    def field(self, parent, label, widget_factory, pady=(10, 0)):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", padx=6, pady=pady)
        field_label(box, label).pack(anchor="w", pady=(0, 6))
        widget = widget_factory(box)
        widget.pack(fill="x")
        return widget

    def row(self, parent=None):
        frame = ctk.CTkFrame(parent or self.body, fg_color="transparent")
        frame.pack(fill="x")
        frame.grid_columnconfigure((0, 1), weight=1, uniform="col")
        return frame

    def grid_field(self, row, column, label, widget_factory):
        box = ctk.CTkFrame(row, fg_color="transparent")
        box.grid(row=0, column=column, sticky="ew", padx=6, pady=(10, 0))
        field_label(box, label).pack(anchor="w", pady=(0, 6))
        widget = widget_factory(box)
        widget.pack(fill="x")
        return widget

    def section(self, text):
        ctk.CTkLabel(self.body, text=text.upper(), font=F(11, "bold"),
                     text_color=COLORS["text_subtle"]).pack(anchor="w", padx=6, pady=(20, 0))

    def footer_buttons(self, primary_text, primary_command, variant="primary", cancel_command=None):
        button(self.footer, primary_text, primary_command, variant=variant, width=150).pack(side="right")
        button(self.footer, "Cancel", cancel_command or self.destroy, variant="secondary",
               width=100).pack(side="right", padx=(0, 10))


class ConfirmDialog(BaseModal):
    def __init__(self, parent, title="Confirm action", message="Are you sure?", confirm_text="Confirm", is_danger=False):
        super().__init__(parent, title=title, width=460, height=240, scroll=False)
        self.result = False
        ctk.CTkLabel(self.body, text=message, font=F(13), text_color=COLORS["text_muted"],
                     wraplength=400, justify="left", anchor="w").pack(anchor="w", fill="x", padx=6, pady=(4, 0))
        self.footer_buttons(confirm_text, self.on_confirm, variant="danger" if is_danger else "primary",
                            cancel_command=self.on_cancel)
        self.wait_window(self)

    def on_confirm(self):
        self.result = True
        self.destroy()

    def on_cancel(self):
        self.result = False
        self.destroy()


class MessageDialog(BaseModal):
    def __init__(self, parent, title="Notice", message="", is_error=False):
        super().__init__(parent, title=title, width=460, height=240, scroll=False)
        tone = "danger" if is_error else "success"
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=(4, 0))
        ctk.CTkLabel(row, text="!" if is_error else "✓", width=28, height=28, corner_radius=14,
                     fg_color=COLORS[tone], text_color="#FFFFFF", font=F(13, "bold")).pack(side="left", anchor="n")
        ctk.CTkLabel(row, text=message, font=F(13), text_color=COLORS["text_muted"],
                     wraplength=360, justify="left", anchor="w").pack(side="left", fill="x", expand=True, padx=(12, 0))
        button(self.footer, "OK", self.destroy, width=100).pack(side="right")
        self.wait_window(self)


class MemberModalDialog(BaseModal):
    """Add or edit a member."""

    def __init__(self, parent, db, member_data=None):
        editing = bool(member_data)
        super().__init__(
            parent,
            title="Edit member" if editing else "Register new member",
            subtitle="Fields marked * are required. Phone numbers must be unique.",
            width=560, height=800,
        )
        self.db = db
        self.member_data = member_data

        self.trainers = self.db.get_all_trainers()
        self.trainer_map = {f"{t['full_name']} · {t['specialization']}": t["trainer_id"] for t in self.trainers}
        self.trainer_names = ["Unassigned"] + list(self.trainer_map)

        self.lbl_error = self.error_label()

        self.section("Personal details")
        self.ent_name = self.field(self.body, "Full name *", lambda p: entry(p, placeholder_text="e.g. Alexander Clark"))
        r = self.row()
        self.ent_phone = self.grid_field(r, 0, "Phone *", lambda p: entry(p, placeholder_text="+880 1712-345678"))
        self.ent_email = self.grid_field(r, 1, "Email *", lambda p: entry(p, placeholder_text="name@example.com"))
        r = self.row()
        self.cmb_gender = self.grid_field(r, 0, "Gender", lambda p: combo(p, values=GENDERS, state="readonly"))
        self.ent_join_date = self.grid_field(r, 1, "Join date (YYYY-MM-DD) *", lambda p: entry(p))
        self.ent_join_date.insert(0, date.today().strftime("%Y-%m-%d"))

        self.section("Training")
        self.cmb_trainer = self.field(self.body, "Personal trainer",
                                      lambda p: combo(p, values=self.trainer_names, state="readonly"))

        self.section("Emergency contact (optional)")
        r = self.row()
        self.ent_ec_name = self.grid_field(r, 0, "Contact name", lambda p: entry(p, placeholder_text="e.g. Jane Clark"))
        self.ent_ec_phone = self.grid_field(r, 1, "Contact phone", lambda p: entry(p, placeholder_text="+880 1812-345678"))

        if editing:
            self.ent_name.insert(0, member_data.get("full_name", ""))
            self.ent_phone.insert(0, member_data.get("phone", ""))
            self.ent_email.insert(0, member_data.get("email", ""))
            self.cmb_gender.set(member_data.get("gender", "Male"))
            self.ent_join_date.delete(0, "end")
            self.ent_join_date.insert(0, member_data.get("join_date", date.today().strftime("%Y-%m-%d")))
            if member_data.get("emergency_contact_name"):
                self.ent_ec_name.insert(0, member_data["emergency_contact_name"])
            if member_data.get("emergency_contact_phone"):
                self.ent_ec_phone.insert(0, member_data["emergency_contact_phone"])
            tid = member_data.get("trainer_id")
            current = next((name for name, t_id in self.trainer_map.items() if t_id == tid), "Unassigned")
            self.cmb_trainer.set(current)
        else:
            self.cmb_gender.set("Male")
            self.cmb_trainer.set("Unassigned")

        self.footer_buttons("Save changes" if editing else "Register member", self.save)
        self.wait_window(self)

    def save(self):
        name = self.ent_name.get().strip()
        phone = self.ent_phone.get().strip()
        email = self.ent_email.get().strip()
        gender = self.cmb_gender.get().strip()
        join_date = self.ent_join_date.get().strip()
        ec_name = self.ent_ec_name.get().strip()
        ec_phone = self.ent_ec_phone.get().strip()

        if not name or not phone or not email or not join_date:
            self.lbl_error.configure(text="Please fill in all required fields (*).")
            return
        try:
            datetime.strptime(join_date, "%Y-%m-%d")
        except ValueError:
            self.lbl_error.configure(text="Invalid join date. Use YYYY-MM-DD.")
            return

        trainer_id = self.trainer_map.get(self.cmb_trainer.get().strip())
        fields = dict(full_name=name, phone=phone, email=email, gender=gender, join_date=join_date,
                      trainer_id=trainer_id, emergency_contact_name=ec_name, emergency_contact_phone=ec_phone)
        try:
            if self.member_data:
                self.result = self.db.update_member(member_id=self.member_data["member_id"], **fields)
            else:
                self.result = self.db.add_member(**fields)
            self.destroy()
        except ValueError as ex:
            self.lbl_error.configure(text=str(ex))


class TrainerModalDialog(BaseModal):
    """Add or edit a trainer."""

    def __init__(self, parent, db, trainer_data=None):
        editing = bool(trainer_data)
        super().__init__(
            parent,
            title="Edit trainer" if editing else "Add new trainer",
            subtitle="Salary must be greater than zero. Phone numbers must be unique.",
            width=540, height=520,
        )
        self.db = db
        self.trainer_data = trainer_data

        self.lbl_error = self.error_label()
        self.ent_name = self.field(self.body, "Full name *", lambda p: entry(p, placeholder_text="e.g. Jordan Reed"))
        r = self.row()
        self.ent_phone = self.grid_field(r, 0, "Phone *", lambda p: entry(p, placeholder_text="+880 1912-345678"))
        self.cmb_spec = self.grid_field(r, 1, "Specialization *", lambda p: combo(p, values=SPECIALIZATIONS))
        r = self.row()
        self.ent_salary = self.grid_field(r, 0, "Monthly salary ($) *", lambda p: entry(p, placeholder_text="4500.00"))
        self.ent_hire = self.grid_field(r, 1, "Hire date (YYYY-MM-DD) *", lambda p: entry(p))

        if editing:
            self.ent_name.insert(0, trainer_data.get("full_name", ""))
            self.ent_phone.insert(0, trainer_data.get("phone", ""))
            self.cmb_spec.set(trainer_data.get("specialization", SPECIALIZATIONS[0]))
            self.ent_salary.insert(0, f"{float(trainer_data.get('monthly_salary', 0)):.2f}")
            self.ent_hire.insert(0, trainer_data.get("hire_date", date.today().strftime("%Y-%m-%d")))
        else:
            self.cmb_spec.set(SPECIALIZATIONS[0])
            self.ent_salary.insert(0, "4200.00")
            self.ent_hire.insert(0, date.today().strftime("%Y-%m-%d"))

        self.footer_buttons("Save trainer", self.save)
        self.wait_window(self)

    def save(self):
        name = self.ent_name.get().strip()
        phone = self.ent_phone.get().strip()
        spec = self.cmb_spec.get().strip()
        salary_str = self.ent_salary.get().strip()
        hire_date = self.ent_hire.get().strip()

        if not name or not phone or not spec or not salary_str or not hire_date:
            self.lbl_error.configure(text="Please fill in all fields.")
            return
        try:
            salary = float(salary_str)
        except ValueError:
            self.lbl_error.configure(text="Invalid salary amount.")
            return
        if salary <= 0:
            self.lbl_error.configure(text="Salary must be greater than 0.")
            return
        try:
            datetime.strptime(hire_date, "%Y-%m-%d")
        except ValueError:
            self.lbl_error.configure(text="Invalid hire date. Use YYYY-MM-DD.")
            return

        fields = dict(full_name=name, phone=phone, specialization=spec, monthly_salary=salary, hire_date=hire_date)
        try:
            if self.trainer_data:
                self.result = self.db.update_trainer(trainer_id=self.trainer_data["trainer_id"], **fields)
            else:
                self.result = self.db.add_trainer(**fields)
            self.destroy()
        except ValueError as ex:
            self.lbl_error.configure(text=str(ex))


class PackageModalDialog(BaseModal):
    """Add or edit a membership plan."""

    def __init__(self, parent, db, package_data=None):
        editing = bool(package_data)
        super().__init__(
            parent,
            title="Edit plan" if editing else "New membership plan",
            subtitle="Plan names must be unique. Duration is in days.",
            width=540, height=540,
        )
        self.db = db
        self.package_data = package_data

        self.lbl_error = self.error_label()
        self.ent_name = self.field(self.body, "Plan name *", lambda p: entry(p, placeholder_text="e.g. Annual Platinum"))
        r = self.row()
        self.ent_dur = self.grid_field(r, 0, "Duration (days) *", lambda p: entry(p, placeholder_text="30, 90, 365"))
        self.ent_fee = self.grid_field(r, 1, "Fee ($) *", lambda p: entry(p, placeholder_text="99.99"))

        box = ctk.CTkFrame(self.body, fg_color="transparent")
        box.pack(fill="x", padx=6, pady=(10, 0))
        field_label(box, "Description").pack(anchor="w", pady=(0, 6))
        self.txt_desc = ctk.CTkTextbox(box, height=100, corner_radius=8, border_width=1,
                                       border_color=COLORS["border"], fg_color=COLORS["input"],
                                       text_color=COLORS["text"], font=F(13))
        self.txt_desc.pack(fill="x")

        if editing:
            self.ent_name.insert(0, package_data.get("package_name", ""))
            self.ent_dur.insert(0, str(package_data.get("duration_days", 30)))
            self.ent_fee.insert(0, f"{float(package_data.get('fee', 0)):.2f}")
            self.txt_desc.insert("1.0", package_data.get("description", ""))
        else:
            self.ent_dur.insert(0, "30")
            self.ent_fee.insert(0, "49.99")

        self.footer_buttons("Save plan", self.save)
        self.wait_window(self)

    def save(self):
        name = self.ent_name.get().strip()
        dur_str = self.ent_dur.get().strip()
        fee_str = self.ent_fee.get().strip()
        desc = self.txt_desc.get("1.0", "end-1c").strip()

        if not name or not dur_str or not fee_str:
            self.lbl_error.configure(text="Please fill in all required fields.")
            return
        try:
            dur = int(dur_str)
        except ValueError:
            self.lbl_error.configure(text="Duration must be a whole number of days.")
            return
        if dur <= 0:
            self.lbl_error.configure(text="Duration must be at least 1 day.")
            return
        try:
            fee = float(fee_str)
        except ValueError:
            self.lbl_error.configure(text="Invalid fee amount.")
            return
        if fee < 0:
            self.lbl_error.configure(text="Fee cannot be negative.")
            return

        fields = dict(package_name=name, duration_days=dur, fee=fee, description=desc)
        try:
            if self.package_data:
                self.result = self.db.update_package(package_id=self.package_data["package_id"], **fields)
            else:
                self.result = self.db.add_package(**fields)
            self.destroy()
        except ValueError as ex:
            self.lbl_error.configure(text=str(ex))


class SubscriptionModalDialog(BaseModal):
    """Record a payment: new subscription or renewal."""

    def __init__(self, parent, db, preselected_member_id=None):
        super().__init__(
            parent,
            title="Record payment",
            subtitle="Renewals start when the current plan ends. The end date is calculated from the plan duration.",
            width=580, height=600,
        )
        self.db = db

        self.members = self.db.get_all_members_detailed()
        self.packages = self.db.get_all_packages()
        self.member_map = {f"{m['full_name']} · {m['phone']} · #{m['member_id']}": m["member_id"] for m in self.members}
        self.member_options = list(self.member_map)
        self.pkg_map = {f"{p['package_name']} · {p['duration_days']} days · ${p['fee']:.2f}": p for p in self.packages}
        self.pkg_options = list(self.pkg_map)

        self.lbl_error = self.error_label()
        self.cmb_member = self.field(self.body, "Member *", lambda p: combo(
            p, values=self.member_options, command=self.on_member_selected, state="readonly"))
        self.cmb_package = self.field(self.body, "Plan *", lambda p: combo(
            p, values=self.pkg_options, command=self.on_package_selected, state="readonly"))

        r = self.row()
        self.ent_start = self.grid_field(r, 0, "Start date (YYYY-MM-DD) *", lambda p: entry(p))
        self.ent_start.insert(0, date.today().strftime("%Y-%m-%d"))
        self.ent_start.bind("<KeyRelease>", lambda e: self.update_end_date_preview())
        self.lbl_end_preview = self.grid_field(r, 1, "End date (calculated)", lambda p: ctk.CTkLabel(
            p, text="—", height=38, corner_radius=8, fg_color=COLORS["primary_soft"],
            text_color=COLORS["primary"], font=F(13, "bold")))

        r = self.row()
        self.ent_amt = self.grid_field(r, 0, "Amount paid ($) *", lambda p: entry(p))
        self.cmb_meth = self.grid_field(r, 1, "Payment method *", lambda p: combo(p, values=PAYMENT_METHODS, state="readonly"))
        self.cmb_meth.set("Credit Card")

        if preselected_member_id:
            for opt, m_id in self.member_map.items():
                if m_id == preselected_member_id:
                    self.cmb_member.set(opt)
                    self.on_member_selected(opt)
                    break
        elif self.member_options:
            self.cmb_member.set(self.member_options[0])
            self.on_member_selected(self.member_options[0])

        if self.pkg_options:
            self.cmb_package.set(self.pkg_options[0])
            self.on_package_selected(self.pkg_options[0])

        self.footer_buttons("Record payment", self.save, variant="success")
        self.wait_window(self)

    def on_member_selected(self, choice):
        m_id = self.member_map.get(choice)
        if m_id:
            self.ent_start.delete(0, "end")
            self.ent_start.insert(0, self.db.get_renewal_start_date(m_id))
        self.update_end_date_preview()

    def on_package_selected(self, choice):
        pkg = self.pkg_map.get(choice)
        if pkg:
            self.ent_amt.delete(0, "end")
            self.ent_amt.insert(0, f"{pkg['fee']:.2f}")
            self.update_end_date_preview()

    def update_end_date_preview(self):
        pkg = self.pkg_map.get(self.cmb_package.get())
        start_str = self.ent_start.get().strip()
        if pkg and start_str:
            try:
                end_str = self.db.calculate_end_date(start_str, pkg["duration_days"])
                self.lbl_end_preview.configure(text=f"{end_str}  ({pkg['duration_days']} days)")
            except Exception:
                self.lbl_end_preview.configure(text="Invalid start date")
        else:
            self.lbl_end_preview.configure(text="—")

    def save(self):
        m_id = self.member_map.get(self.cmb_member.get())
        pkg = self.pkg_map.get(self.cmb_package.get())
        start_date = self.ent_start.get().strip()
        amt_str = self.ent_amt.get().strip()
        method = self.cmb_meth.get().strip()

        if not m_id or not pkg or not start_date or not amt_str:
            self.lbl_error.configure(text="Please fill in all fields.")
            return
        try:
            amt = float(amt_str)
        except ValueError:
            self.lbl_error.configure(text="Invalid amount.")
            return
        if amt < 0:
            self.lbl_error.configure(text="Amount paid cannot be negative.")
            return
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            self.lbl_error.configure(text="Invalid start date. Use YYYY-MM-DD.")
            return

        try:
            self.result = self.db.add_subscription(
                member_id=m_id, package_id=pkg["package_id"], start_date_str=start_date,
                amount_paid=amt, payment_method=method,
            )
            self.destroy()
        except ValueError as ex:
            self.lbl_error.configure(text=str(ex))


def export_with_message(parent, tree, name):
    """Export a table's visible rows to CSV and tell the user where the file went."""
    from ui.export import export_tree, display_path
    try:
        path, count = export_tree(tree, name)
    except OSError as ex:
        MessageDialog(parent, title="Export failed", message=str(ex), is_error=True)
        return
    MessageDialog(parent, title="Export complete",
                  message=f"Saved {count} row(s) to {display_path(path)}")


class MemberProfileDialog(BaseModal):
    """Read-only member profile: details, lifetime stats and full payment history.
    result is "edit" or "renew" when the user picks one of those actions."""

    def __init__(self, parent, db, member_id, can_edit=False, can_renew=False):
        self.profile = db.get_member_profile(member_id)
        m = self.profile["member"]
        stats = self.profile["stats"]
        super().__init__(
            parent, title=m["full_name"],
            subtitle=f"Member #{m['member_id']}  ·  joined {m['join_date']}  ·  {m['gender']}",
            width=860, height=720,
        )
        self.db = db

        # Stat tiles
        tiles = ctk.CTkFrame(self.body, fg_color="transparent")
        tiles.pack(fill="x", padx=6, pady=(6, 0))
        status = m["status"]
        ends = m["sub_end"] if m["sub_end"] != "-" else "—"
        if status == "Expiring Soon":
            ends_caption = f"in {m['days_left']} day(s)"
        elif status == "Expired":
            ends_caption = f"{-m['days_left']} day(s) ago"
        elif status == "Active":
            ends_caption = f"{m['days_left']} days left"
        else:
            ends_caption = "no plan yet"
        for i, (label, value, caption, color) in enumerate([
            ("Status", status_text(status, m.get("days_left")).lstrip("●○ "), m["package_name"],
             COLORS[STATUS_COLORS.get(status, "text_muted")]),
            ("Plan ends", ends, ends_caption, COLORS["text"]),
            ("Total spent", f"${stats['total_spent']:,.2f}", f"{stats['payments']} payment(s)", COLORS["text"]),
            ("Days purchased", str(stats["days_purchased"]),
             f"since {stats['first_payment']}" if stats["first_payment"] else "—", COLORS["text"]),
        ]):
            tiles.grid_columnconfigure(i, weight=1, uniform="tile")
            t = card(tiles, fg_color=COLORS["surface_alt"])
            t.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            ctk.CTkLabel(t, text=label.upper(), font=F(10, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=14, pady=(12, 0))
            ctk.CTkLabel(t, text=value, font=F(18, "bold"), text_color=color).pack(anchor="w", padx=14)
            ctk.CTkLabel(t, text=caption, font=F(11), text_color=COLORS["text_muted"]).pack(anchor="w", padx=14, pady=(0, 12))

        # Details in three columns
        details = ctk.CTkFrame(self.body, fg_color="transparent")
        details.pack(fill="x", padx=6, pady=(16, 0))
        emergency = (f"{m['emergency_contact_name']}\n{m['emergency_contact_phone']}"
                     if m.get("emergency_contact_name") else "Not provided")
        groups = [
            ("Contact", [("Phone", m["phone"]), ("Email", m["email"])]),
            ("Membership", [("Trainer", m["trainer_name"]), ("Current plan", m["package_name"])]),
            ("Emergency contact", [("Name / phone", emergency)]),
        ]
        for i, (title, items) in enumerate(groups):
            details.grid_columnconfigure(i, weight=1, uniform="det")
            col = ctk.CTkFrame(details, fg_color="transparent")
            col.grid(row=0, column=i, sticky="nw", padx=(0 if i == 0 else 16, 0))
            ctk.CTkLabel(col, text=title.upper(), font=F(10, "bold"), text_color=COLORS["text_subtle"]).pack(anchor="w")
            for label, value in items:
                ctk.CTkLabel(col, text=label, font=F(11), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(6, 0))
                ctk.CTkLabel(col, text=value, font=F(13, "bold"), text_color=COLORS["text"],
                             justify="left", anchor="w").pack(anchor="w")

        # Payment history
        hist_head = ctk.CTkFrame(self.body, fg_color="transparent")
        hist_head.pack(fill="x", padx=6, pady=(20, 6))
        ctk.CTkLabel(hist_head, text="Payment history", font=F(15, "bold"), text_color=COLORS["text"]).pack(side="left")
        if stats["last_payment"]:
            ctk.CTkLabel(hist_head, text=f"last payment {stats['last_payment']}", font=F(12),
                         text_color=COLORS["text_muted"]).pack(side="right")

        setup_treeview_style()
        wrap, self.tree = table(self.body, [
            ("sub_id", "Txn", 55, "center"),
            ("package", "Plan", 140, "w"),
            ("paid_on", "Paid on", 90, "center"),
            ("start", "Starts", 90, "center"),
            ("end", "Ends", 90, "center"),
            ("amount", "Amount", 80, "e"),
            ("method", "Method", 100, "center"),
            ("status", "Status", 115, "center"),
        ], height=6)
        wrap.pack(fill="x", padx=6, pady=(0, 6))
        style_tree_tags(self.tree)
        for i, p in enumerate(self.profile["payments"]):
            insert_row(self.tree, p["sub_id"], (
                p["sub_id"], p["package_name"], p.get("payment_date", p["start_date"]), p["start_date"],
                p["end_date"], f"${p['amount_paid']:,.2f}", p["payment_method"],
                status_text(p["status"], p.get("days_left")),
            ), i, p["status"])
        if not self.profile["payments"]:
            ctk.CTkLabel(self.body, text="No payments recorded yet.", font=F(12),
                         text_color=COLORS["text_muted"]).pack(anchor="w", padx=6)

        # Footer actions
        if can_renew:
            button(self.footer, "Renew plan", lambda: self._finish("renew"), variant="success", width=120).pack(side="right")
        if can_edit:
            button(self.footer, "Edit details", lambda: self._finish("edit"), variant="secondary",
                   width=120).pack(side="right", padx=(0, 10))
        button(self.footer, "Close", self.destroy, variant="secondary", width=90).pack(side="left")

        self.wait_window(self)

    def _finish(self, action):
        self.result = action
        self.destroy()
