"""
Activity log: every payment, member change, price change and trainer removal,
recorded by the database triggers in sql/triggers.sql (or by the JSON backend).
"""

import customtkinter as ctk
from ui.theme import (
    COLORS, button, card, entry, combo, kpi_card, page_header, selection_bar, table,
    style_tree_tags, insert_row, clear_tree, setup_treeview_style,
)
from ui.dialogs import export_with_message

ACTION_LABELS = {
    "PAYMENT_RECORDED": "Payment recorded",
    "PAYMENT_VOIDED": "Payment voided",
    "MEMBER_ADDED": "Member added",
    "MEMBER_UPDATED": "Member updated",
    "MEMBER_DELETED": "Member deleted",
    "PRICE_CHANGED": "Price changed",
    "TRAINER_DELETED": "Trainer removed",
    "DEMO_RESET": "Demo data reset",
}
# Rows that removed something get the red tint, recorded payments the amber one
ACTION_TINT = {"PAYMENT_VOIDED": "Expired", "MEMBER_DELETED": "Expired", "TRAINER_DELETED": "Expired",
               "PRICE_CHANGED": "Expiring Soon"}


class ActivityView(ctk.CTkFrame):
    def __init__(self, parent, db, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.app = app_controller
        self.entries = []
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        source = ("Recorded automatically by MySQL triggers" if getattr(self.db, "triggers_enabled", False)
                  else "Recorded automatically by the application")
        actions = page_header(self, "Activity log", f"{source} — who changed what, and when.")
        if self.app.can("data.export"):
            button(actions, "Export CSV", lambda: export_with_message(self.winfo_toplevel(), self.tree, "activity_log"),
                   variant="secondary", width=110).pack(side="left", padx=(0, 8))
        button(actions, "Refresh", self.refresh_data, variant="secondary", width=90).pack(side="left")

        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.pack(fill="x", padx=28, pady=(0, 14))
        self.kpi = {}
        for i, (key, label, accent) in enumerate([
            ("total", "Events logged", "primary"),
            ("payments", "Payments recorded", "success"),
            ("removals", "Deletions & voids", "danger"),
        ]):
            kpis.grid_columnconfigure(i, weight=1, uniform="kpi")
            frame, value, caption = kpi_card(kpis, label, accent)
            frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            self.kpi[key] = (value, caption)

        toolbar = card(self)
        toolbar.pack(fill="x", padx=28, pady=(0, 14))
        inner = ctk.CTkFrame(toolbar, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)
        self.ent_search = entry(inner, placeholder_text="Search details or staff user")
        self.ent_search.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.ent_search.bind("<KeyRelease>", lambda e: self.apply_filters())
        self.cmb_action = combo(inner, values=["All events"] + list(ACTION_LABELS.values()), width=190,
                                state="readonly", command=lambda c: self.apply_filters())
        self.cmb_action.pack(side="left")
        self.cmb_action.set("All events")

        _, self.lbl_hint = selection_bar(self)

        wrap, self.tree = table(self, [
            ("time", "Time", 160, "center"),
            ("user", "Staff user", 110, "center"),
            ("action", "Event", 150, "w"),
            ("record", "Record", 140, "center"),
            ("details", "Details", 560, "w"),
        ])
        wrap.pack(fill="both", expand=True, padx=28, pady=(0, 24))

    def refresh_data(self):
        setup_treeview_style()
        style_tree_tags(self.tree)
        self.entries = self.db.get_audit_log(1000)
        self.kpi["total"][0].configure(text=str(len(self.entries)))
        self.kpi["total"][1].configure(text=f"latest {self.entries[0]['event_time']}" if self.entries else "nothing yet")
        payments = sum(1 for e in self.entries if e["action"] == "PAYMENT_RECORDED")
        self.kpi["payments"][0].configure(text=str(payments))
        self.kpi["payments"][1].configure(text="since the last reset")
        removals = sum(1 for e in self.entries if e["action"] in ("PAYMENT_VOIDED", "MEMBER_DELETED", "TRAINER_DELETED"))
        self.kpi["removals"][0].configure(text=str(removals))
        self.kpi["removals"][1].configure(text="members, trainers, payments")
        self.apply_filters()

    def apply_filters(self):
        query = self.ent_search.get().strip().lower()
        wanted = self.cmb_action.get()
        clear_tree(self.tree)
        shown = 0
        for e in self.entries:
            label = ACTION_LABELS.get(e["action"], e["action"].replace("_", " ").title())
            if wanted != "All events" and label != wanted:
                continue
            if query and query not in (e.get("details") or "").lower() and query not in (e.get("app_user") or "").lower():
                continue
            record = f"{e['table_name']} #{e['record_id']}" if e.get("record_id") is not None else e["table_name"]
            insert_row(self.tree, e["log_id"], (e["event_time"], e["app_user"], label, record, e.get("details") or ""),
                       shown, ACTION_TINT.get(e["action"]))
            shown += 1
        self.lbl_hint.configure(text=f"Showing {shown} of {len(self.entries)} events (newest first)",
                                text_color=COLORS["text_muted"])
