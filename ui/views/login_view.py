"""
Authentication & Access Control View:
Split-screen sign-in page — brand panel on the left, credentials form on the right.
"""

import customtkinter as ctk
from ui.theme import COLORS, F, button, entry, field_label

FEATURES = [
    ("Member lifecycle", "Track active, expiring and expired plans automatically."),
    ("Billing & renewals", "Every payment linked to a plan, end dates calculated for you."),
    ("Live analytics", "Revenue by month and method, trainer workload at a glance."),
]

DEMO_ACCOUNTS = [("Admin", "admin", "admin123"), ("Manager", "manager", "manager123"), ("Staff", "staff", "staff123")]


class LoginView(ctk.CTkFrame):
    def __init__(self, parent, db, on_login_success):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.db = db
        self.on_login_success = on_login_success

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=5, uniform="split")
        self.grid_columnconfigure(1, weight=6, uniform="split")

        self._build_brand_panel()
        self._build_form()

    # -------------------------------------------------------------
    def _build_brand_panel(self):
        panel = ctk.CTkFrame(self, corner_radius=0, fg_color=("#4338CA", "#1E1B4B"))
        panel.grid(row=0, column=0, sticky="nsew")

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.78)

        logo_row = ctk.CTkFrame(inner, fg_color="transparent")
        logo_row.pack(anchor="w", pady=(0, 40))
        logo = ctk.CTkFrame(logo_row, width=44, height=44, corner_radius=12, fg_color="#FFFFFF")
        logo.pack(side="left")
        logo.pack_propagate(False)
        ctk.CTkLabel(logo, text="IP", font=F(17, "bold"), text_color="#4338CA").pack(expand=True)
        ctk.CTkLabel(logo_row, text="IronPulse", font=F(22, "bold"), text_color="#FFFFFF").pack(side="left", padx=12)

        ctk.CTkLabel(
            inner, text="Run your gym\nwith clarity.", font=F(34, "bold"), text_color="#FFFFFF", justify="left"
        ).pack(anchor="w")
        ctk.CTkLabel(
            inner, text="Members, plans, payments and trainers — managed in one place.",
            font=F(14), text_color="#C7D2FE", justify="left", wraplength=380
        ).pack(anchor="w", pady=(12, 36))

        for title, desc in FEATURES:
            row = ctk.CTkFrame(inner, fg_color="transparent")
            row.pack(anchor="w", fill="x", pady=8)
            ctk.CTkLabel(row, text="✓", width=26, height=26, corner_radius=13, fg_color="#6366F1",
                         text_color="#FFFFFF", font=F(12, "bold")).pack(side="left", anchor="n")
            text = ctk.CTkFrame(row, fg_color="transparent")
            text.pack(side="left", padx=12, fill="x", expand=True)
            ctk.CTkLabel(text, text=title, font=F(14, "bold"), text_color="#FFFFFF", anchor="w").pack(anchor="w")
            ctk.CTkLabel(text, text=desc, font=F(12), text_color="#C7D2FE", anchor="w", justify="left",
                         wraplength=340).pack(anchor="w")

    # -------------------------------------------------------------
    def _build_form(self):
        side = ctk.CTkFrame(self, corner_radius=0, fg_color=COLORS["bg"])
        side.grid(row=0, column=1, sticky="nsew")

        form = ctk.CTkFrame(side, fg_color="transparent", width=380)
        form.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(form, text="Welcome back", font=F(28, "bold"), text_color=COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(form, text="Sign in with your staff account to continue.", font=F(13),
                     text_color=COLORS["text_muted"]).pack(anchor="w", pady=(4, 28))

        field_label(form, "Username").pack(anchor="w", pady=(0, 6))
        self.ent_user = entry(form, placeholder_text="e.g. admin", width=380, height=44)
        self.ent_user.pack(fill="x", pady=(0, 16))
        self.ent_user.bind("<Return>", lambda e: self.ent_pass.focus_set())

        field_label(form, "Password").pack(anchor="w", pady=(0, 6))
        self.ent_pass = entry(form, placeholder_text="Enter your password", show="•", width=380, height=44)
        self.ent_pass.pack(fill="x", pady=(0, 10))
        self.ent_pass.bind("<Return>", lambda e: self.perform_login())

        self.show_pass_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            form, text="Show password", variable=self.show_pass_var, command=self.toggle_show_pass,
            font=F(12), text_color=COLORS["text_muted"], checkbox_width=18, checkbox_height=18,
            corner_radius=5, border_width=2, fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            border_color=COLORS["border"]
        ).pack(anchor="w", pady=(0, 18))

        self.lbl_error = ctk.CTkLabel(form, text="", text_color=COLORS["danger"], font=F(12, "bold"), anchor="w")
        self.lbl_error.pack(anchor="w", fill="x")

        button(form, "Sign in", self.perform_login, height=44, font=F(14, "bold")).pack(fill="x", pady=(6, 28))

        divider = ctk.CTkFrame(form, fg_color="transparent")
        divider.pack(fill="x", pady=(0, 14))
        ctk.CTkFrame(divider, height=1, fg_color=COLORS["border"]).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(divider, text="  Demo accounts  ", font=F(11), text_color=COLORS["text_subtle"]).pack(side="left")
        ctk.CTkFrame(divider, height=1, fg_color=COLORS["border"]).pack(side="left", fill="x", expand=True)

        demo = ctk.CTkFrame(form, fg_color="transparent")
        demo.pack(fill="x")
        for i, (label, user, pwd) in enumerate(DEMO_ACCOUNTS):
            demo.grid_columnconfigure(i, weight=1, uniform="demo")
            button(demo, label, lambda u=user, p=pwd: self.fill_demo(u, p), variant="secondary",
                   height=36, font=F(12, "bold")).grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 4, 0))

        self.after(100, self.ent_user.focus_set)

    # -------------------------------------------------------------
    def toggle_show_pass(self):
        self.ent_pass.configure(show="" if self.show_pass_var.get() else "•")

    def fill_demo(self, user, pwd):
        self.ent_user.delete(0, "end")
        self.ent_user.insert(0, user)
        self.ent_pass.delete(0, "end")
        self.ent_pass.insert(0, pwd)
        self.perform_login()

    def perform_login(self):
        user = self.ent_user.get().strip()
        pwd = self.ent_pass.get().strip()
        if not user or not pwd:
            self.lbl_error.configure(text="Please enter both username and password.")
            return
        user_info = self.db.authenticate(user, pwd)
        if user_info:
            self.lbl_error.configure(text="")
            self.on_login_success(user_info)
        else:
            self.lbl_error.configure(text="Invalid username or password.")
