"""
Member Management: registration, editing, deletion (ON DELETE CASCADE),
renewals, live search and status / trainer filters.
"""

import customtkinter as ctk
from ui.theme import (
    set_enabled,
    COLORS, button, card, entry, combo, page_header, selection_bar, table,
    style_tree_tags, insert_row, clear_tree, status_text, setup_treeview_style,
)
from ui.dialogs import (
    MemberModalDialog, MemberProfileDialog, SubscriptionModalDialog, ConfirmDialog, MessageDialog,
    export_with_message,
)

STATUS_FILTERS = ["All statuses", "Active", "Expiring Soon", "Expired", "No Subscription"]
TRAINER_FILTERS = ["All trainers", "With trainer", "Unassigned"]


class MembersView(ctk.CTkFrame):
    def __init__(self, parent, db, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.app = app_controller
        self.members_cache = []
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        actions = page_header(self, "Members", "Register members, assign trainers and track plan status.")
        if self.app.can("data.export"):
            button(actions, "Export CSV", lambda: export_with_message(self.winfo_toplevel(), self.tree, "members"),
                   variant="secondary", width=110).pack(side="left", padx=(0, 8))
        self.btn_add = button(actions, "Register member", self.add_member, width=150,
                              state="normal" if self.app.can("member.add") else "disabled")
        self.btn_add.pack(side="left")

        # Toolbar
        toolbar = card(self)
        toolbar.pack(fill="x", padx=28, pady=(0, 14))
        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        self.ent_search = entry(inner, placeholder_text="Search by name, phone or email")
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.ent_search.bind("<KeyRelease>", lambda e: self.apply_filters())
        self.cmb_status = combo(inner, values=STATUS_FILTERS, width=160, state="readonly",
                                command=lambda c: self.apply_filters())
        self.cmb_status.pack(side="left", padx=(0, 10))
        self.cmb_status.set(STATUS_FILTERS[0])
        self.cmb_trainer_filter = combo(inner, values=TRAINER_FILTERS, width=150, state="readonly",
                                        command=lambda c: self.apply_filters())
        self.cmb_trainer_filter.pack(side="left")
        self.cmb_trainer_filter.set(TRAINER_FILTERS[0])

        # Selection bar
        bar, self.lbl_selected_info = selection_bar(self)
        self.btn_profile = button(bar, "View profile", self.view_profile, variant="secondary", width=110, height=32)
        self.btn_edit = button(bar, "Edit", self.edit_selected, variant="secondary", width=80, height=32)
        self.btn_renew = button(bar, "Renew plan", self.renew_selected, variant="success", width=110, height=32)
        self.btn_delete = button(bar, "Delete", self.delete_selected, variant="danger", width=80, height=32)
        for b in (self.btn_edit, self.btn_renew, self.btn_delete, self.btn_profile):
            b.pack(side="right", padx=(8, 0))

        # Table
        wrap, self.tree = table(self, [
            ("id", "ID", 60, "center"),
            ("name", "Name", 170, "w"),
            ("phone", "Phone", 130, "w"),
            ("email", "Email", 175, "w"),
            ("gender", "Gender", 75, "center"),
            ("join_date", "Joined", 95, "center"),
            ("trainer", "Trainer", 150, "w"),
            ("package", "Current plan", 150, "w"),
            ("sub_end", "Ends", 95, "center"),
            ("status", "Status", 140, "center"),
        ])
        wrap.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.view_profile())

    def refresh_data(self):
        setup_treeview_style()
        style_tree_tags(self.tree)
        self.members_cache = self.db.get_all_members_detailed()
        self.apply_filters()

    def apply_filters(self):
        query = self.ent_search.get().strip().lower()
        status_filter = self.cmb_status.get()
        trainer_filter = self.cmb_trainer_filter.get()

        clear_tree(self.tree)
        shown = 0
        for m in self.members_cache:
            if query and not (query in m["full_name"].lower() or query in m["phone"].lower()
                              or query in m["email"].lower()):
                continue
            if status_filter != STATUS_FILTERS[0] and m.get("status") != status_filter:
                continue
            unassigned = m.get("trainer_name") == "Unassigned"
            if (trainer_filter == "With trainer" and unassigned) or (trainer_filter == "Unassigned" and not unassigned):
                continue
            insert_row(self.tree, m["member_id"], (
                m["member_id"], m["full_name"], m["phone"], m["email"], m["gender"], m["join_date"],
                m["trainer_name"], m["package_name"], m["sub_end"], status_text(m["status"], m.get("days_left")),
            ), shown, m["status"])
            shown += 1
        self.shown_count = shown
        self.on_select(None)

    def on_select(self, event):
        selected = self.tree.selection()
        mem = None
        if selected:
            m_id = int(selected[0])
            mem = next((m for m in self.members_cache if m["member_id"] == m_id), None)
        if mem:
            emergency = (f"{mem['emergency_contact_name']} ({mem['emergency_contact_phone']})"
                         if mem.get("emergency_contact_name") else "not provided")
            self.lbl_selected_info.configure(
                text=f"{mem['full_name']}  ·  {status_text(mem['status'], mem.get('days_left'))}  ·  Emergency contact: {emergency}",
                text_color=COLORS["text"])
        else:
            total = len(self.members_cache)
            self.lbl_selected_info.configure(
                text=f"Showing {getattr(self, 'shown_count', total)} of {total} members · double-click a row to open the profile",
                text_color=COLORS["text_muted"])
        set_enabled(self.btn_profile, bool(mem))
        for btn, perm in ((self.btn_edit, "member.edit"), (self.btn_renew, "billing.record"),
                          (self.btn_delete, "member.delete")):
            set_enabled(btn, bool(mem) and self.app.can(perm))

    def _selected_id(self, permission):
        selected = self.tree.selection()
        if not selected or not self.app.can(permission):
            return None
        return int(selected[0])

    def view_profile(self):
        selected = self.tree.selection()
        if not selected:
            return
        m_id = int(selected[0])
        dlg = MemberProfileDialog(self.winfo_toplevel(), self.db, m_id,
                                  can_edit=self.app.can("member.edit"),
                                  can_renew=self.app.can("billing.record"))
        if dlg.result == "edit":
            self.edit_selected()
        elif dlg.result == "renew":
            self.renew_selected()

    def add_member(self):
        if not self.app.can("member.add"):
            return
        if MemberModalDialog(self.winfo_toplevel(), self.db).result:
            self.app.notify_data_changed()

    def edit_selected(self):
        m_id = self._selected_id("member.edit")
        mem = self.db.get_member_by_id(m_id) if m_id else None
        if mem and MemberModalDialog(self.winfo_toplevel(), self.db, member_data=mem).result:
            self.app.notify_data_changed()

    def renew_selected(self):
        m_id = self._selected_id("billing.record")
        if m_id and SubscriptionModalDialog(self.winfo_toplevel(), self.db, preselected_member_id=m_id).result:
            self.app.notify_data_changed()

    def delete_selected(self):
        m_id = self._selected_id("member.delete")
        mem = self.db.get_member_by_id(m_id) if m_id else None
        if not mem:
            return
        confirm = ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete member?",
            message=(f"'{mem['full_name']}' (#{m_id}) will be removed together with all of their "
                     f"payment records (ON DELETE CASCADE). This cannot be undone."),
            confirm_text="Delete member",
            is_danger=True
        )
        if confirm.result:
            deleted_subs = self.db.delete_member(m_id)
            MessageDialog(self.winfo_toplevel(), title="Member deleted",
                          message=f"'{mem['full_name']}' was deleted along with {deleted_subs} payment record(s).")
            self.app.notify_data_changed()
