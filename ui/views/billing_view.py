"""
Billing & Renewals: payment ledger with search and filters, renewals and voiding entries.
"""

import customtkinter as ctk
from ui.theme import (
    set_enabled,
    COLORS, button, card, entry, combo, kpi_card, page_header, selection_bar, table,
    style_tree_tags, insert_row, clear_tree, status_text, setup_treeview_style,
)
from ui.dialogs import SubscriptionModalDialog, ConfirmDialog, MessageDialog, export_with_message
from common import PAYMENT_METHODS

STATUS_FILTERS = ["All statuses", "Active", "Expiring Soon", "Expired"]


class BillingView(ctk.CTkFrame):
    def __init__(self, parent, db, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.app = app_controller
        self.subs_cache = []
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        actions = page_header(self, "Billing & renewals", "Every payment, the plan it bought and when it ends.")
        if self.app.can("data.export"):
            button(actions, "Export CSV", lambda: export_with_message(self.winfo_toplevel(), self.tree, "payments"),
                   variant="secondary", width=110).pack(side="left", padx=(0, 8))
        button(actions, "Record payment", self.add_subscription, variant="success", width=150,
               state="normal" if self.app.can("billing.record") else "disabled").pack(side="left")

        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.pack(fill="x", padx=28, pady=(0, 14))
        self.kpi = {}
        for i, (key, label, accent) in enumerate([
            ("count", "Transactions", "primary"),
            ("filtered", "Filtered total", "success"),
            ("average", "Average payment", "info"),
        ]):
            kpis.grid_columnconfigure(i, weight=1, uniform="kpi")
            frame, value, caption = kpi_card(kpis, label, accent)
            frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            self.kpi[key] = (value, caption)

        toolbar = card(self)
        toolbar.pack(fill="x", padx=28, pady=(0, 14))
        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        self.ent_search = entry(inner, placeholder_text="Search by member, phone, plan or transaction ID")
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.ent_search.bind("<KeyRelease>", lambda e: self.apply_filters())
        self.cmb_method = combo(inner, values=["All methods"] + PAYMENT_METHODS, width=160, state="readonly",
                                command=lambda c: self.apply_filters())
        self.cmb_method.pack(side="left", padx=(0, 10))
        self.cmb_method.set("All methods")
        self.cmb_status = combo(inner, values=STATUS_FILTERS, width=150, state="readonly",
                                command=lambda c: self.apply_filters())
        self.cmb_status.pack(side="left")
        self.cmb_status.set(STATUS_FILTERS[0])

        bar, self.lbl_selected = selection_bar(self)
        self.btn_quick_renew = button(bar, "Renew member", self.renew_selected, width=130, height=32)
        self.btn_delete = button(bar, "Void entry", self.delete_selected, variant="danger", width=100, height=32)
        self.btn_quick_renew.pack(side="right", padx=(8, 0))
        self.btn_delete.pack(side="right", padx=(8, 0))

        wrap, self.tree = table(self, [
            ("sub_id", "Txn", 70, "center"),
            ("member", "Member", 170, "w"),
            ("phone", "Phone", 130, "w"),
            ("package", "Plan", 160, "w"),
            ("paid_on", "Paid on", 95, "center"),
            ("start_date", "Starts", 95, "center"),
            ("end_date", "Ends", 95, "center"),
            ("amount", "Amount", 95, "e"),
            ("method", "Method", 120, "center"),
            ("status", "Status", 120, "center"),
        ])
        wrap.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.renew_selected())

    def refresh_data(self):
        setup_treeview_style()
        style_tree_tags(self.tree)
        self.subs_cache = self.db.get_all_subscriptions_detailed()
        self.apply_filters()

    def apply_filters(self):
        query = self.ent_search.get().strip().lower()
        method_filter = self.cmb_method.get()
        status_filter = self.cmb_status.get()

        clear_tree(self.tree)
        shown, total = 0, 0.0
        for s in self.subs_cache:
            if query and not (query in str(s["sub_id"]) or query in s["member_name"].lower()
                              or query in s["member_phone"].lower() or query in s["package_name"].lower()):
                continue
            if method_filter != "All methods" and s.get("payment_method") != method_filter:
                continue
            if status_filter != STATUS_FILTERS[0] and s.get("status") != status_filter:
                continue
            insert_row(self.tree, s["sub_id"], (
                s["sub_id"], s["member_name"], s["member_phone"], s["package_name"],
                s.get("payment_date", s["start_date"]), s["start_date"], s["end_date"],
                f"${s['amount_paid']:,.2f}", s["payment_method"], status_text(s["status"], s.get("days_left")),
            ), shown, s["status"])
            shown += 1
            total += s["amount_paid"]

        all_total = sum(s["amount_paid"] for s in self.subs_cache)
        self.kpi["count"][0].configure(text=str(len(self.subs_cache)))
        self.kpi["count"][1].configure(text=f"${all_total:,.2f} collected all-time")
        self.kpi["filtered"][0].configure(text=f"${total:,.2f}")
        self.kpi["filtered"][1].configure(text=f"{shown} transaction(s) shown")
        self.kpi["average"][0].configure(text=f"${(total / shown) if shown else 0:,.2f}")
        self.kpi["average"][1].configure(text="for the current filter")
        self.shown_count = shown
        self.on_select(None)

    def on_select(self, event):
        selected = self.tree.selection()
        sub = None
        if selected:
            sid = int(selected[0])
            sub = next((s for s in self.subs_cache if s["sub_id"] == sid), None)
        if sub:
            self.lbl_selected.configure(
                text=f"Txn #{sub['sub_id']}  ·  {sub['member_name']}  ·  {sub['package_name']}  ·  ${sub['amount_paid']:,.2f}",
                text_color=COLORS["text"])
        else:
            self.lbl_selected.configure(text="Select a transaction to renew the member or void the entry.",
                                        text_color=COLORS["text_muted"])
        set_enabled(self.btn_quick_renew, sub and self.app.can("billing.record"))
        set_enabled(self.btn_delete, sub and self.app.can("billing.void"))

    def _selected_sub(self, permission):
        selected = self.tree.selection()
        if not selected or not self.app.can(permission):
            return None
        sid = int(selected[0])
        return next((s for s in self.subs_cache if s["sub_id"] == sid), None)

    def add_subscription(self):
        if self.app.can("billing.record") and SubscriptionModalDialog(self.winfo_toplevel(), self.db).result:
            self.app.notify_data_changed()

    def renew_selected(self):
        sub = self._selected_sub("billing.record")
        if sub and SubscriptionModalDialog(self.winfo_toplevel(), self.db,
                                           preselected_member_id=sub["member_id"]).result:
            self.app.notify_data_changed()

    def delete_selected(self):
        sub = self._selected_sub("billing.void")
        if not sub:
            return
        confirm = ConfirmDialog(
            self.winfo_toplevel(),
            title="Void transaction?",
            message=(f"Transaction #{sub['sub_id']} for {sub['member_name']} "
                     f"(${sub['amount_paid']:,.2f}) will be permanently removed from the ledger."),
            confirm_text="Void entry",
            is_danger=True
        )
        if confirm.result:
            self.db.delete_subscription(sub["sub_id"])
            MessageDialog(self.winfo_toplevel(), title="Transaction voided",
                          message=f"Transaction #{sub['sub_id']} has been removed.")
            self.app.notify_data_changed()
