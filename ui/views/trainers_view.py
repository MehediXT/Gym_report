"""
Trainer Directory: profiles, specializations, payroll and workload
(deleting a trainer unassigns members via ON DELETE SET NULL).
"""

import customtkinter as ctk
from ui.theme import (
    set_enabled,
    COLORS, button, card, entry, kpi_card, page_header, selection_bar, table,
    style_tree_tags, insert_row, clear_tree, setup_treeview_style,
)
from ui.dialogs import TrainerModalDialog, ConfirmDialog, MessageDialog, export_with_message


class TrainersView(ctk.CTkFrame):
    def __init__(self, parent, db, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.app = app_controller
        self.trainers_cache = []
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        actions = page_header(self, "Trainers", "Specializations, payroll and how many members each trainer coaches.")
        if self.app.can("data.export"):
            button(actions, "Export CSV", lambda: export_with_message(self.winfo_toplevel(), self.tree, "trainers"),
                   variant="secondary", width=110).pack(side="left", padx=(0, 8))
        button(actions, "Add trainer", self.add_trainer, width=130,
               state="normal" if self.app.can("trainer.add") else "disabled").pack(side="left")

        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.pack(fill="x", padx=28, pady=(0, 14))
        self.kpi = {}
        for i, (key, label, accent) in enumerate([
            ("count", "Trainers", "primary"),
            ("assigned", "Members coached", "info"),
            ("payroll", "Monthly payroll", "success"),
        ]):
            kpis.grid_columnconfigure(i, weight=1, uniform="kpi")
            frame, value, caption = kpi_card(kpis, label, accent)
            frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            self.kpi[key] = (value, caption)

        toolbar = card(self)
        toolbar.pack(fill="x", padx=28, pady=(0, 14))
        self.ent_search = entry(toolbar, placeholder_text="Search by name, phone or specialization")
        self.ent_search.pack(fill="x", padx=14, pady=12)
        self.ent_search.bind("<KeyRelease>", lambda e: self.apply_filters())

        bar, self.lbl_hint = selection_bar(self)
        self.btn_edit = button(bar, "Edit", self.edit_selected, variant="secondary", width=80, height=32)
        self.btn_delete = button(bar, "Delete", self.delete_selected, variant="danger", width=80, height=32)
        self.btn_delete.pack(side="right", padx=(8, 0))
        self.btn_edit.pack(side="right", padx=(8, 0))

        wrap, self.tree = table(self, [
            ("id", "ID", 60, "center"),
            ("name", "Name", 180, "w"),
            ("phone", "Phone", 130, "w"),
            ("spec", "Specialization", 210, "w"),
            ("salary", "Monthly salary", 120, "e"),
            ("hire_date", "Hired", 100, "center"),
            ("workload", "Active / total", 110, "center"),
            ("members", "Assigned members", 260, "w"),
        ])
        wrap.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    def refresh_data(self):
        setup_treeview_style()
        style_tree_tags(self.tree)
        self.trainers_cache = self.db.get_all_trainers()
        payroll = sum(t["monthly_salary"] for t in self.trainers_cache)
        assigned = sum(t["assigned_count"] for t in self.trainers_cache)
        active = sum(t["active_count"] for t in self.trainers_cache)
        n = len(self.trainers_cache)
        self.kpi["count"][0].configure(text=str(n))
        self.kpi["count"][1].configure(text="on staff")
        self.kpi["assigned"][0].configure(text=str(assigned))
        self.kpi["assigned"][1].configure(text=f"{active} with a current plan")
        self.kpi["payroll"][0].configure(text=f"${payroll:,.2f}")
        self.kpi["payroll"][1].configure(text=f"avg ${payroll / n:,.0f} per trainer" if n else "")
        self.apply_filters()

    def apply_filters(self):
        query = self.ent_search.get().strip().lower()
        clear_tree(self.tree)
        shown = 0
        for t in self.trainers_cache:
            if query and not (query in t["full_name"].lower() or query in t["phone"].lower()
                              or query in t["specialization"].lower()):
                continue
            insert_row(self.tree, t["trainer_id"], (
                t["trainer_id"], t["full_name"], t["phone"], t["specialization"],
                f"${t['monthly_salary']:,.2f}", t["hire_date"],
                f"{t['active_count']} / {t['assigned_count']}",
                ", ".join(t["assigned_members"]) or "—",
            ), shown)
            shown += 1
        self.shown_count = shown
        self.on_select(None)

    def on_select(self, event):
        selected = self.tree.selection()
        trainer = None
        if selected:
            tid = int(selected[0])
            trainer = next((t for t in self.trainers_cache if t["trainer_id"] == tid), None)
        if trainer:
            self.lbl_hint.configure(text=f"{trainer['full_name']}  ·  {trainer['specialization']}  ·  "
                                         f"{trainer['assigned_count']} assigned member(s)", text_color=COLORS["text"])
        else:
            self.lbl_hint.configure(text=f"Showing {getattr(self, 'shown_count', 0)} of {len(self.trainers_cache)} "
                                         f"trainers · select a row for actions", text_color=COLORS["text_muted"])
        set_enabled(self.btn_edit, trainer and self.app.can("trainer.edit"))
        set_enabled(self.btn_delete, trainer and self.app.can("trainer.delete"))

    def _selected_trainer(self, permission):
        selected = self.tree.selection()
        if not selected or not self.app.can(permission):
            return None
        return self.db.get_trainer_by_id(int(selected[0]))

    def add_trainer(self):
        if self.app.can("trainer.add") and TrainerModalDialog(self.winfo_toplevel(), self.db).result:
            self.app.notify_data_changed()

    def edit_selected(self):
        trainer = self._selected_trainer("trainer.edit")
        if trainer and TrainerModalDialog(self.winfo_toplevel(), self.db, trainer_data=trainer).result:
            self.app.notify_data_changed()

    def delete_selected(self):
        trainer = self._selected_trainer("trainer.delete")
        if not trainer:
            return
        confirm = ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete trainer?",
            message=(f"'{trainer['full_name']}' will be removed. Their members stay registered "
                     f"but become unassigned (ON DELETE SET NULL)."),
            confirm_text="Delete trainer",
            is_danger=True
        )
        if confirm.result:
            reassigned = self.db.delete_trainer(trainer["trainer_id"])
            MessageDialog(self.winfo_toplevel(), title="Trainer deleted",
                          message=f"Trainer removed. {reassigned} member(s) are now unassigned.")
            self.app.notify_data_changed()
