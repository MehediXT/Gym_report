"""
Membership Plans: create, edit and delete plans (ON DELETE RESTRICT protects
plans that are referenced by payment records).
"""

import customtkinter as ctk
from ui.theme import (
    set_enabled,
    COLORS, F, button, card, page_header, selection_bar, table,
    style_tree_tags, insert_row, clear_tree, setup_treeview_style,
)
from ui.dialogs import PackageModalDialog, ConfirmDialog, MessageDialog


class PackagesView(ctk.CTkFrame):
    def __init__(self, parent, db, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.app = app_controller
        self.packages_cache = []
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        actions = page_header(self, "Membership plans", "Pricing, duration and how many members are on each plan.")
        button(actions, "New plan", self.add_package, width=120,
               state="normal" if self.app.can("package.add") else "disabled").pack(side="left")

        self.cards_row = ctk.CTkScrollableFrame(self, height=150, orientation="horizontal", fg_color="transparent",
                                                scrollbar_button_color=COLORS["border"])
        self.cards_row.pack(fill="x", padx=22, pady=(0, 10))

        bar, self.lbl_selected = selection_bar(self)
        self.btn_edit = button(bar, "Edit", self.edit_selected, variant="secondary", width=80, height=32)
        self.btn_delete = button(bar, "Delete", self.delete_selected, variant="danger", width=80, height=32)
        self.btn_delete.pack(side="right", padx=(8, 0))
        self.btn_edit.pack(side="right", padx=(8, 0))

        wrap, self.tree = table(self, [
            ("id", "ID", 60, "center"),
            ("name", "Plan", 190, "w"),
            ("duration", "Duration", 100, "center"),
            ("fee", "Fee", 100, "e"),
            ("subscribers", "Active / all-time", 130, "center"),
            ("description", "Description", 420, "w"),
        ])
        wrap.pack(fill="both", expand=True, padx=28, pady=(0, 24))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    def _plan_card(self, p):
        c = card(self.cards_row, width=220, height=132)
        c.pack(side="left", padx=6, pady=4)
        c.pack_propagate(False)
        ctk.CTkLabel(c, text=p["package_name"], font=F(13, "bold"), text_color=COLORS["text"], anchor="w").pack(anchor="w", padx=16, pady=(14, 0))
        price = ctk.CTkFrame(c, fg_color="transparent")
        price.pack(anchor="w", padx=16, pady=(6, 0))
        ctk.CTkLabel(price, text=f"${p['fee']:,.2f}", font=F(24, "bold"), text_color=COLORS["primary"]).pack(side="left")
        ctk.CTkLabel(price, text=f" / {p['duration_days']} days", font=F(12), text_color=COLORS["text_muted"]).pack(side="left", anchor="s", pady=(0, 4))
        active = p.get("active_subscribers", 0)
        ctk.CTkLabel(c, text=f"● {active} active member{'s' if active != 1 else ''}", font=F(12, "bold"),
                     text_color=COLORS["success"] if active else COLORS["text_subtle"]).pack(anchor="w", padx=16, pady=(8, 0))

    def refresh_data(self):
        setup_treeview_style()
        style_tree_tags(self.tree)
        self.packages_cache = self.db.get_all_packages()

        for w in self.cards_row.winfo_children():
            w.destroy()
        for p in self.packages_cache:
            self._plan_card(p)

        clear_tree(self.tree)
        for i, p in enumerate(self.packages_cache):
            insert_row(self.tree, p["package_id"], (
                p["package_id"], p["package_name"], f"{p['duration_days']} days", f"${p['fee']:,.2f}",
                f"{p.get('active_subscribers', 0)} / {p.get('total_subscriptions', 0)}", p["description"],
            ), i)
        self.on_select(None)

    def on_select(self, event):
        selected = self.tree.selection()
        pkg = None
        if selected:
            pid = int(selected[0])
            pkg = next((p for p in self.packages_cache if p["package_id"] == pid), None)
        if pkg:
            refs = pkg.get("total_subscriptions", 0)
            note = f"used by {refs} payment record(s), cannot be deleted" if refs else "not used yet, can be deleted"
            self.lbl_selected.configure(text=f"{pkg['package_name']}  ·  ${pkg['fee']:,.2f} / {pkg['duration_days']} days  ·  {note}",
                                        text_color=COLORS["text"])
        else:
            self.lbl_selected.configure(text=f"{len(self.packages_cache)} plans · select a row for actions",
                                        text_color=COLORS["text_muted"])
        set_enabled(self.btn_edit, pkg and self.app.can("package.edit"))
        set_enabled(self.btn_delete, pkg and self.app.can("package.delete"))

    def _selected_package(self, permission):
        selected = self.tree.selection()
        if not selected or not self.app.can(permission):
            return None
        return self.db.get_package_by_id(int(selected[0]))

    def add_package(self):
        if self.app.can("package.add") and PackageModalDialog(self.winfo_toplevel(), self.db).result:
            self.app.notify_data_changed()

    def edit_selected(self):
        pkg = self._selected_package("package.edit")
        if pkg and PackageModalDialog(self.winfo_toplevel(), self.db, package_data=pkg).result:
            self.app.notify_data_changed()

    def delete_selected(self):
        pkg = self._selected_package("package.delete")
        if not pkg:
            return
        confirm = ConfirmDialog(
            self.winfo_toplevel(),
            title="Delete plan?",
            message=(f"Delete '{pkg['package_name']}'? Plans referenced by payment records are protected "
                     f"by ON DELETE RESTRICT and cannot be removed."),
            confirm_text="Delete plan",
            is_danger=True
        )
        if not confirm.result:
            return
        try:
            self.db.delete_package(pkg["package_id"])
            MessageDialog(self.winfo_toplevel(), title="Plan deleted", message=f"'{pkg['package_name']}' was deleted.")
            self.app.notify_data_changed()
        except ValueError as ex:
            MessageDialog(self.winfo_toplevel(), title="Plan is in use", message=str(ex), is_error=True)
