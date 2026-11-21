"""
Dashboard: KPI tiles, renewal action center, revenue breakdowns and trainer workload.
"""

import tkinter as tk
from datetime import date, datetime
import customtkinter as ctk
from ui.theme import (
    COLORS, F, pick, font_family, button, card, kpi_card, page_header, section_title, table,
    style_tree_tags, insert_row, clear_tree, setup_treeview_style,
)
from ui.dialogs import SubscriptionModalDialog, MemberModalDialog, MessageDialog
from ui.export import export_rows, display_path


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, db, app_controller):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.app = app_controller
        self.monthly = []
        self.build_ui()
        self.refresh_data()

    # -------------------------------------------------------------
    def build_ui(self):
        actions = page_header(self, "Dashboard", f"Overview for {date.today().strftime('%A, %d %B %Y')}")
        button(actions, "Refresh", self.refresh_data, variant="secondary", width=90).pack(side="left", padx=(0, 8))
        if self.app.can("data.export"):
            button(actions, "Export report", self.export_report, variant="secondary", width=120).pack(side="left", padx=(0, 8))
        button(actions, "New member", self.quick_add_member, variant="secondary", width=120,
               state="normal" if self.app.can("member.add") else "disabled").pack(side="left", padx=(0, 8))
        button(actions, "Record payment", self.quick_renew, width=140,
               state="normal" if self.app.can("billing.record") else "disabled").pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=COLORS["border"])
        self.scroll.pack(fill="both", expand=True, padx=(16, 8), pady=(0, 16))
        body = self.scroll

        # KPI tiles
        kpis = ctk.CTkFrame(body, fg_color="transparent")
        kpis.pack(fill="x", padx=4, pady=(0, 16))
        self.kpi = {}
        for i, (key, label, accent) in enumerate([
            ("revenue", "Total revenue", "primary"),
            ("members", "Members", "info"),
            ("active", "Active plans", "success"),
            ("expiring", "Expiring soon", "warning"),
            ("expired", "Expired", "danger"),
        ]):
            kpis.grid_columnconfigure(i, weight=1, uniform="kpi")
            frame, value, caption = kpi_card(kpis, label, accent)
            frame.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            self.kpi[key] = (value, caption)

        # Action center + revenue by method
        mid = ctk.CTkFrame(body, fg_color="transparent")
        mid.pack(fill="x", padx=4, pady=(0, 16))
        mid.grid_columnconfigure(0, weight=3, uniform="mid")
        mid.grid_columnconfigure(1, weight=2, uniform="mid")

        alert = card(mid)
        alert.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        head = ctk.CTkFrame(alert, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(18, 12))
        self.alert_title = section_title(head, "Renewals due", "Plans ending within the next 7 days")
        self.alert_title.pack(side="left")
        self.btn_renew_alert = button(head, "Renew selected", self.renew_from_alert, variant="warning", width=130, height=32,
                                      state="normal" if self.app.can("billing.record") else "disabled")
        self.btn_renew_alert.pack(side="right")

        wrap, self.alert_tree = table(alert, [
            ("name", "Member", 170, "w"),
            ("phone", "Phone", 120, "w"),
            ("package", "Plan", 150, "w"),
            ("end_date", "Ends", 100, "center"),
            ("days_left", "Days left", 90, "center"),
        ], height=5)
        wrap.configure(border_width=0, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.alert_tree.bind("<Double-1>", lambda e: self.renew_from_alert())
        self.lbl_alert_empty = ctk.CTkLabel(alert, text="", font=F(12), text_color=COLORS["text_muted"])
        self.lbl_alert_empty.pack(anchor="w", padx=20, pady=(0, 14))

        pay = card(mid)
        pay.grid(row=0, column=1, sticky="nsew")
        section_title(pay, "Revenue by payment method", "All-time share of collected fees").pack(anchor="w", padx=20, pady=(18, 12))
        self.pay_frame = ctk.CTkFrame(pay, fg_color="transparent")
        self.pay_frame.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        # Monthly revenue chart
        monthly = card(body)
        monthly.pack(fill="x", padx=4, pady=(0, 16))
        mhead = ctk.CTkFrame(monthly, fg_color="transparent")
        mhead.pack(fill="x", padx=20, pady=(18, 4))
        section_title(mhead, "Monthly revenue", "Last 6 months, by payment date").pack(side="left")
        self.lbl_monthly_total = ctk.CTkLabel(mhead, text="", font=F(20, "bold"), text_color=COLORS["text"])
        self.lbl_monthly_total.pack(side="right")
        self.chart = tk.Canvas(monthly, height=220, highlightthickness=0, bd=0)
        self.chart.pack(fill="x", padx=20, pady=(4, 18))
        self.chart.bind("<Configure>", lambda e: self.draw_chart())

        # Trainer workload
        wl = card(body)
        wl.pack(fill="x", padx=4, pady=(0, 8))
        section_title(wl, "Trainer workload", "Members with a current plan vs. all assigned members").pack(anchor="w", padx=20, pady=(18, 8))
        wl_wrap, self.wl_tree = table(wl, [
            ("tname", "Trainer", 170, "w"),
            ("spec", "Specialization", 200, "w"),
            ("salary", "Monthly salary", 120, "e"),
            ("trainees", "Active / total", 110, "center"),
            ("members", "Assigned members", 280, "w"),
        ], height=5)
        wl_wrap.configure(border_width=0, fg_color="transparent")
        wl_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # -------------------------------------------------------------
    def refresh_data(self):
        setup_treeview_style()
        for tree in (self.alert_tree, self.wl_tree):
            style_tree_tags(tree)
        m = self.db.get_dashboard_metrics()
        sc = m["status_counts"]

        self.kpi["revenue"][0].configure(text=f"${m['total_revenue']:,.2f}")
        self.kpi["revenue"][1].configure(text=f"{m['total_packages']} plans offered")
        self.kpi["members"][0].configure(text=str(m["total_members"]))
        self.kpi["members"][1].configure(text=f"{m['total_trainers']} trainers on staff")
        self.kpi["active"][0].configure(text=str(sc["Active"]))
        self.kpi["active"][1].configure(text="more than 7 days left")
        self.kpi["expiring"][0].configure(text=str(sc["Expiring Soon"]))
        self.kpi["expiring"][1].configure(text="within 7 days")
        self.kpi["expired"][0].configure(text=str(sc["Expired"]))
        no_plan = sc.get("No Subscription", 0)
        self.kpi["expired"][1].configure(text=f"{no_plan} without a plan" if no_plan else "need renewal")

        # Renewals due
        clear_tree(self.alert_tree)
        expiring = m["expiring_soon_list"]
        for i, mem in enumerate(expiring):
            d = mem["days_left"]
            days = "Today" if d == 0 else f"{d} day{'s' if d != 1 else ''}"
            insert_row(self.alert_tree, mem["member_id"],
                       (mem["full_name"], mem["phone"], mem["package_name"], mem["sub_end"], days), i, "Expiring Soon")
        self.lbl_alert_empty.configure(
            text="Nothing due this week." if not expiring else
            f"{len(expiring)} member{'s' if len(expiring) != 1 else ''} to contact · double-click a row to renew"
        )

        # Revenue by method
        for w in self.pay_frame.winfo_children():
            w.destroy()
        total = max(m["total_revenue"], 1.0)
        for method, amt in sorted(m["revenue_by_method"].items(), key=lambda x: x[1], reverse=True):
            pct = amt / total
            row = ctk.CTkFrame(self.pay_frame, fg_color="transparent")
            row.pack(fill="x", pady=(0, 12))
            top = ctk.CTkFrame(row, fg_color="transparent")
            top.pack(fill="x")
            ctk.CTkLabel(top, text=method, font=F(12, "bold"), text_color=COLORS["text"]).pack(side="left")
            ctk.CTkLabel(top, text=f"${amt:,.2f}", font=F(12, "bold"), text_color=COLORS["text"]).pack(side="right")
            ctk.CTkLabel(top, text=f"{pct * 100:.0f}%  ", font=F(12), text_color=COLORS["text_muted"]).pack(side="right")
            bar = ctk.CTkProgressBar(row, height=6, corner_radius=3, progress_color=COLORS["primary"],
                                     fg_color=COLORS["neutral"])
            bar.pack(fill="x", pady=(6, 0))
            bar.set(pct)

        # Monthly chart
        self.monthly = m.get("monthly_revenue", [])
        self.lbl_monthly_total.configure(text=f"${sum(x['total'] for x in self.monthly):,.2f}")
        self.draw_chart()

        # Trainer workload
        clear_tree(self.wl_tree)
        for i, t in enumerate(m["trainers_workload"]):
            insert_row(self.wl_tree, t["trainer_id"], (
                t["full_name"], t["specialization"], f"${t['monthly_salary']:,.2f}",
                f"{t['active_count']} / {t['assigned_count']}",
                ", ".join(t["assigned_members"]) or "—",
            ), i)

    def draw_chart(self):
        c = self.chart
        c.delete("all")
        c.configure(bg=pick("surface"))
        w, h = c.winfo_width(), int(c.cget("height"))
        if w < 50 or not self.monthly:
            return
        family = font_family()
        top, bottom, left = 24, 30, 8
        plot_h = h - top - bottom
        peak = max([x["total"] for x in self.monthly] + [1.0])
        grid, muted, text = pick("border"), pick("text_muted"), pick("text")
        for i in range(4):
            y = top + plot_h * i / 3
            c.create_line(left, y, w, y, fill=grid)
        n = len(self.monthly)
        slot = (w - left) / n
        bar_w = min(56, slot * 0.5)
        current = date.today().strftime("%Y-%m")
        for i, x in enumerate(self.monthly):
            cx = left + slot * i + slot / 2
            bh = plot_h * (x["total"] / peak)
            color = pick("primary") if x["month"] == current else pick(("#A5B4FC", "#3F4694"))
            if bh > 0:
                c.create_rectangle(cx - bar_w / 2, top + plot_h - bh, cx + bar_w / 2, top + plot_h, fill=color, width=0)
                c.create_text(cx, top + plot_h - bh - 10, text=f"${x['total']:,.0f}", fill=text, font=(family, 10, "bold"))
            label = datetime.strptime(x["month"], "%Y-%m").strftime("%b %Y")
            c.create_text(cx, h - bottom / 2, text=label, fill=muted, font=(family, 10))

    # -------------------------------------------------------------
    def export_report(self):
        """One CSV with the dashboard figures: KPIs, monthly revenue, revenue by method, workload."""
        m = self.db.get_dashboard_metrics()
        rows = [("Summary", "Total revenue", f"{m['total_revenue']:.2f}"),
                ("Summary", "Members", m["total_members"]),
                ("Summary", "Trainers", m["total_trainers"]),
                ("Summary", "Plans offered", m["total_packages"])]
        rows += [("Member status", k, v) for k, v in m["status_counts"].items()]
        rows += [("Monthly revenue", x["month"], f"{x['total']:.2f}") for x in m["monthly_revenue"]]
        rows += [("Revenue by method", k, f"{v:.2f}") for k, v in m["revenue_by_method"].items()]
        rows += [("Trainer workload", t["full_name"], f"{t['active_count']} active / {t['assigned_count']} total")
                 for t in m["trainers_workload"]]
        rows += [("Renewals due", f"{x['full_name']} ({x['phone']})", x["sub_end"]) for x in m["expiring_soon_list"]]
        try:
            path, count = export_rows("dashboard_report", ["Section", "Item", "Value"], rows)
        except OSError as ex:
            MessageDialog(self.winfo_toplevel(), title="Export failed", message=str(ex), is_error=True)
            return
        MessageDialog(self.winfo_toplevel(), title="Report exported",
                      message=f"Saved {count} line(s) to {display_path(path)}")

    def renew_from_alert(self):
        selected = self.alert_tree.selection()
        if not selected or not self.app.can("billing.record"):
            return
        dlg = SubscriptionModalDialog(self.winfo_toplevel(), self.db, preselected_member_id=int(selected[0]))
        if dlg.result:
            self.app.notify_data_changed()

    def quick_add_member(self):
        if not self.app.can("member.add"):
            return
        dlg = MemberModalDialog(self.winfo_toplevel(), self.db)
        if dlg.result:
            self.app.notify_data_changed()

    def quick_renew(self):
        if not self.app.can("billing.record"):
            return
        dlg = SubscriptionModalDialog(self.winfo_toplevel(), self.db)
        if dlg.result:
            self.app.notify_data_changed()
