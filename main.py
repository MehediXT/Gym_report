#!/usr/bin/env python3
"""
Main Application Entry Point:
Gym & Fitness Club Member & Subscription Management System
Desktop GUI Application built with Python and CustomTkinter.
"""

import bootstrap  # noqa: F401  (sets up optional user-space Tk libraries)
import customtkinter as ctk

from db_factory import create_database
from common import role_can
from ui.theme import COLORS, F, button, setup_treeview_style
from ui.dialogs import ConfirmDialog, MessageDialog
from ui.views.login_view import LoginView
from ui.views.dashboard_view import DashboardView
from ui.views.members_view import MembersView
from ui.views.trainers_view import TrainersView
from ui.views.packages_view import PackagesView
from ui.views.billing_view import BillingView
from ui.views.activity_view import ActivityView

NAV_ITEMS = [
    ("dashboard", "Dashboard"),
    ("members", "Members"),
    ("trainers", "Trainers"),
    ("packages", "Membership Plans"),
    ("billing", "Billing & Renewals"),
    ("activity", "Activity Log"),       # Admin / Manager only
]


def initials(name):
    clean = name.split("(")[0].strip()
    parts = [p for p in clean.split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


class GymApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("IronPulse Fitness — Member & Subscription Management")
        self.geometry("1320x840")
        self.minsize(1120, 700)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLORS["bg"])

        self.db, self.db_warning = create_database()
        self.current_user = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.show_login_screen()
        if self.db_warning:
            self.after(400, lambda: MessageDialog(self, title="MySQL unavailable", message=self.db_warning, is_error=True))

    # -------------------------------------------------------------
    # Screen switching
    # -------------------------------------------------------------
    def show_login_screen(self):
        self.clear_container()
        self.container.grid_columnconfigure(1, weight=0)
        self.login_view = LoginView(self.container, self.db, on_login_success=self.on_login_success)
        self.login_view.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def on_login_success(self, user_info):
        self.current_user = user_info
        self.db.set_session_user(user_info["username"])
        self.clear_container()
        self.build_main_shell()
        self.navigate_to("dashboard")

    def logout(self):
        confirm = ConfirmDialog(
            self,
            title="Sign out",
            message=f"Sign out of '{self.current_user['username']}'?",
            confirm_text="Sign out"
        )
        if confirm.result:
            self.current_user = None
            self.db.set_session_user(None)
            self.show_login_screen()

    def can(self, permission):
        """Role-based access check for the signed-in user (see common.ROLE_PERMISSIONS)."""
        return bool(self.current_user) and role_can(self.current_user.get("role"), permission)

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # -------------------------------------------------------------
    # Main shell: sidebar + content
    # -------------------------------------------------------------
    def build_main_shell(self):
        self.container.grid_columnconfigure(0, weight=0)
        self.container.grid_columnconfigure(1, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self.container, width=248, corner_radius=0, fg_color=COLORS["sidebar"],
                               border_width=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.pack_propagate(False)
        # hairline divider between sidebar and content
        ctk.CTkFrame(self.container, width=1, corner_radius=0, fg_color=COLORS["border"]).grid(row=0, column=0, sticky="nse")

        # Brand
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(24, 28))
        logo = ctk.CTkFrame(brand, width=36, height=36, corner_radius=10, fg_color=COLORS["primary"])
        logo.pack(side="left")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="IP", font=F(14, "bold"), text_color="#FFFFFF").pack(expand=True)
        brand_text = ctk.CTkFrame(brand, fg_color="transparent")
        brand_text.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(brand_text, text="IronPulse", font=F(17, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(brand_text, text="Fitness Management", font=F(11), text_color=COLORS["text_muted"]).pack(anchor="w")

        ctk.CTkLabel(sidebar, text="MENU", font=F(10, "bold"), text_color=COLORS["text_subtle"]).pack(anchor="w", padx=24, pady=(0, 6))

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12)
        self.nav_items = {}
        for key, label in NAV_ITEMS:
            if key == "activity" and not self.can("audit.view"):
                continue
            row = ctk.CTkFrame(nav, fg_color="transparent", corner_radius=8)
            row.pack(fill="x", pady=2)
            indicator = ctk.CTkFrame(row, width=3, height=22, corner_radius=2, fg_color="transparent")
            indicator.pack(side="left", padx=(0, 6))
            btn = ctk.CTkButton(
                row, text=label, anchor="w", height=40, corner_radius=8,
                font=F(13, "bold"), fg_color="transparent",
                text_color=COLORS["text_muted"], hover_color=COLORS["neutral"],
                command=lambda k=key: self.navigate_to(k)
            )
            btn.pack(side="left", fill="x", expand=True)
            self.nav_items[key] = (indicator, btn)

        # Bottom area
        bottom = ctk.CTkFrame(sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)

        # Storage badge
        is_mysql = getattr(self.db, "backend_name", "") == "MySQL"
        badge = ctk.CTkFrame(bottom, corner_radius=8, fg_color=COLORS["surface_alt"], border_width=1, border_color=COLORS["border"])
        badge.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(badge, text="●", font=F(12), text_color=COLORS["success"] if is_mysql else COLORS["warning"]).pack(side="left", padx=(10, 6), pady=6)
        ctk.CTkLabel(badge, text=getattr(self.db, "backend_label", "Storage"), font=F(11), text_color=COLORS["text_muted"],
                     anchor="w").pack(side="left", fill="x", expand=True, pady=6)

        # Appearance switch
        self.seg_theme = ctk.CTkSegmentedButton(
            bottom, values=["Light", "Dark"], command=self.change_appearance_mode, height=30,
            font=F(12, "bold"), corner_radius=8,
            fg_color=COLORS["neutral"], selected_color=COLORS["primary"], selected_hover_color=COLORS["primary_hover"],
            unselected_color=COLORS["neutral"], unselected_hover_color=COLORS["neutral_hover"],
            text_color=COLORS["text"]
        )
        self.seg_theme.pack(fill="x", pady=(0, 12))
        self.seg_theme.set(ctk.get_appearance_mode())

        if self.can("data.reset"):
            button(bottom, "Reset demo data", self.confirm_reset_demo, variant="secondary", height=32).pack(fill="x", pady=(0, 12))

        # User card
        user_card = ctk.CTkFrame(bottom, corner_radius=10, fg_color=COLORS["surface_alt"], border_width=1, border_color=COLORS["border"])
        user_card.pack(fill="x")
        avatar = ctk.CTkFrame(user_card, width=36, height=36, corner_radius=18, fg_color=COLORS["primary_soft"])
        avatar.pack(side="left", padx=(10, 10), pady=10)
        avatar.pack_propagate(False)
        full_name = self.current_user.get("full_name", self.current_user["username"])
        ctk.CTkLabel(avatar, text=initials(full_name), font=F(12, "bold"), text_color=COLORS["primary"]).pack(expand=True)
        info = ctk.CTkFrame(user_card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)
        ctk.CTkLabel(info, text=full_name.split("(")[0].strip(), font=F(12, "bold"), text_color=COLORS["text"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=self.current_user.get("role", "Staff"), font=F(11), text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")
        ctk.CTkButton(
            user_card, text="Sign out", width=72, height=28, corner_radius=6, font=F(11, "bold"),
            fg_color="transparent", hover_color=COLORS["neutral_hover"], text_color=COLORS["danger"],
            command=self.logout
        ).pack(side="right", padx=(0, 8))

        # Content area
        self.main_area = ctk.CTkFrame(self.container, corner_radius=0, fg_color=COLORS["bg"])
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        setup_treeview_style()
        self.views = {
            "dashboard": DashboardView(self.main_area, self.db, self),
            "members": MembersView(self.main_area, self.db, self),
            "trainers": TrainersView(self.main_area, self.db, self),
            "packages": PackagesView(self.main_area, self.db, self),
            "billing": BillingView(self.main_area, self.db, self),
        }
        if self.can("audit.view"):
            self.views["activity"] = ActivityView(self.main_area, self.db, self)
        self.current_view_key = None

    def navigate_to(self, view_key):
        if view_key not in self.views:
            return
        for key, (indicator, btn) in self.nav_items.items():
            active = key == view_key
            indicator.configure(fg_color=COLORS["primary"] if active else "transparent")
            btn.configure(
                fg_color=COLORS["primary_soft"] if active else "transparent",
                text_color=COLORS["primary"] if active else COLORS["text_muted"],
                hover_color=COLORS["primary_soft"] if active else COLORS["neutral"],
            )
        if self.current_view_key in self.views:
            self.views[self.current_view_key].grid_forget()
        self.views[view_key].grid(row=0, column=0, sticky="nsew")
        self.current_view_key = view_key
        self.views[view_key].refresh_data()

    def notify_data_changed(self):
        for view in self.views.values():
            view.refresh_data()

    def change_appearance_mode(self, mode):
        ctk.set_appearance_mode(mode)
        setup_treeview_style()
        self.notify_data_changed()

    def confirm_reset_demo(self):
        if not self.can("data.reset"):
            return
        confirm = ConfirmDialog(
            self,
            title="Reset demo data?",
            message="All members, trainers, plans and payments will be replaced with the original demo records.",
            confirm_text="Reset data",
            is_danger=True
        )
        if confirm.result:
            self.db.reset_to_demo_data()
            self.notify_data_changed()
            MessageDialog(self, title="Data reset", message="The database now contains the default demo records.")


def main():
    app = GymApp()
    app.mainloop()


if __name__ == "__main__":
    main()
