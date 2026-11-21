"""
Design system for the IronPulse desktop app.

Colour tokens are (light, dark) tuples so CustomTkinter switches them with the
appearance mode. ttk.Treeview does not understand tuples, so tables pick the
right value through `pick()`.
"""

import tkinter.font as tkfont
import customtkinter as ctk
from tkinter import ttk

# -------------------------------------------------------------
# Colour tokens
# -------------------------------------------------------------
COLORS = {
    # Surfaces
    "bg":            ("#F4F6FA", "#0B1120"),
    "sidebar":       ("#FFFFFF", "#0F172A"),
    "surface":       ("#FFFFFF", "#131C2E"),
    "surface_alt":   ("#F8FAFC", "#172238"),
    "border":        ("#E3E8EF", "#1F2A3D"),
    "input":         ("#FFFFFF", "#0F172A"),

    # Text
    "text":          ("#0F172A", "#E6EAF2"),
    "text_muted":    ("#64748B", "#8B95A7"),
    "text_subtle":   ("#94A3B8", "#5B6577"),

    # Brand & semantic
    "primary":       ("#4F46E5", "#6366F1"),
    "primary_hover": ("#4338CA", "#4F46E5"),
    "primary_soft":  ("#EEF2FF", "#1C2140"),
    "success":       ("#059669", "#10B981"),
    "success_hover": ("#047857", "#059669"),
    "warning":       ("#D97706", "#F59E0B"),
    "warning_hover": ("#B45309", "#D97706"),
    "danger":        ("#DC2626", "#EF4444"),
    "danger_hover":  ("#B91C1C", "#DC2626"),
    "info":          ("#0284C7", "#38BDF8"),
    "purple":        ("#7C3AED", "#A78BFA"),

    # Neutral buttons
    "neutral":       ("#EEF1F6", "#1E293B"),
    "neutral_hover": ("#E2E7EF", "#273449"),
}

STATUS_COLORS = {
    "Active": "success",
    "Expiring Soon": "warning",
    "Expired": "danger",
    "No Subscription": "text_muted",
}

# Subtle row tints for rows that need attention (text stays neutral)
STATUS_TINTS = {
    "Expiring Soon": ("#FFF8E6", "#2A2416"),
    "Expired": ("#FDF0F0", "#2B1B24"),
}

PREFERRED_FONTS = ("Inter", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Roboto", "DejaVu Sans")
_font_family = None


def font_family():
    """First installed font from PREFERRED_FONTS (needs a Tk root to exist)."""
    global _font_family
    if _font_family is None:
        try:
            available = set(tkfont.families())
            _font_family = next((f for f in PREFERRED_FONTS if f in available), "TkDefaultFont")
        except Exception:
            return "TkDefaultFont"
    return _font_family


def F(size=13, weight="normal"):
    return ctk.CTkFont(family=font_family(), size=size, weight=weight)


def is_dark():
    return ctk.get_appearance_mode() == "Dark"


def pick(token):
    """Resolve a colour token to a plain hex string for the current mode."""
    value = COLORS.get(token, token)
    if isinstance(value, tuple):
        return value[1] if is_dark() else value[0]
    return value


# -------------------------------------------------------------
# Component helpers
# -------------------------------------------------------------
BUTTON_VARIANTS = {
    "primary":   ("primary", "primary_hover", "#FFFFFF"),
    "success":   ("success", "success_hover", "#FFFFFF"),
    "warning":   ("warning", "warning_hover", "#FFFFFF"),
    "danger":    ("danger", "danger_hover", "#FFFFFF"),
    "secondary": ("neutral", "neutral_hover", None),
}


def button(parent, text, command=None, variant="primary", height=36, **kw):
    fg, hover, text_color = BUTTON_VARIANTS[variant]
    if kw.get("state") == "disabled":
        fg = "neutral"
    opts = dict(
        text=text, command=command, height=height, corner_radius=8,
        fg_color=COLORS[fg], hover_color=COLORS[hover],
        text_color=text_color or COLORS["text"],
        text_color_disabled=COLORS["text_subtle"],
        font=F(13, "bold"),
    )
    if variant == "secondary":
        opts.update(border_width=1, border_color=COLORS["border"])
    opts.update(kw)
    btn = ctk.CTkButton(parent, **opts)
    btn._variant = variant
    return btn


def set_enabled(btn, enabled):
    """Enable/disable a themed button; disabled buttons switch to a neutral fill."""
    fg, hover, _ = BUTTON_VARIANTS[getattr(btn, "_variant", "primary")]
    if enabled:
        btn.configure(state="normal", fg_color=COLORS[fg], hover_color=COLORS[hover])
    else:
        btn.configure(state="disabled", fg_color=COLORS["neutral"])


def card(parent, **kw):
    opts = dict(corner_radius=12, fg_color=COLORS["surface"], border_width=1, border_color=COLORS["border"])
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def entry(parent, **kw):
    opts = dict(height=38, corner_radius=8, border_width=1, border_color=COLORS["border"],
                fg_color=COLORS["input"], text_color=COLORS["text"], font=F(13))
    opts.update(kw)
    return ctk.CTkEntry(parent, **opts)


def combo(parent, **kw):
    opts = dict(height=38, corner_radius=8, border_width=1, border_color=COLORS["border"],
                fg_color=COLORS["input"], button_color=COLORS["neutral"],
                button_hover_color=COLORS["neutral_hover"], text_color=COLORS["text"],
                dropdown_font=F(13), font=F(13))
    opts.update(kw)
    return ctk.CTkComboBox(parent, **opts)


def field_label(parent, text):
    return ctk.CTkLabel(parent, text=text, font=F(12, "bold"), text_color=COLORS["text_muted"], anchor="w")


def section_title(parent, text, subtitle=None):
    box = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(box, text=text, font=F(15, "bold"), text_color=COLORS["text"], anchor="w").pack(anchor="w")
    if subtitle:
        ctk.CTkLabel(box, text=subtitle, font=F(12), text_color=COLORS["text_muted"], anchor="w").pack(anchor="w")
    return box


def page_header(parent, title, subtitle):
    """Page title block. Returns the frame for right-aligned action buttons."""
    header = ctk.CTkFrame(parent, fg_color="transparent")
    header.pack(fill="x", padx=28, pady=(24, 18))

    title_box = ctk.CTkFrame(header, fg_color="transparent")
    title_box.pack(side="left")
    ctk.CTkLabel(title_box, text=title, font=F(24, "bold"), text_color=COLORS["text"]).pack(anchor="w")
    ctk.CTkLabel(title_box, text=subtitle, font=F(13), text_color=COLORS["text_muted"]).pack(anchor="w", pady=(2, 0))

    actions = ctk.CTkFrame(header, fg_color="transparent")
    actions.pack(side="right")
    return actions


def kpi_card(parent, label, accent="primary"):
    """Metric tile with a coloured accent strip. Returns (frame, value_label, caption_label)."""
    c = card(parent)
    ctk.CTkFrame(c, height=3, corner_radius=2, fg_color=COLORS[accent]).pack(fill="x", padx=16, pady=(12, 0))
    ctk.CTkLabel(c, text=label.upper(), font=F(11, "bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=16, pady=(10, 0))
    value = ctk.CTkLabel(c, text="—", font=F(26, "bold"), text_color=COLORS["text"])
    value.pack(anchor="w", padx=16)
    caption = ctk.CTkLabel(c, text="", font=F(11), text_color=COLORS["text_muted"])
    caption.pack(anchor="w", padx=16, pady=(0, 14))
    return c, value, caption


def selection_bar(parent):
    """Row under the filters: hint text on the left, contextual actions on the right."""
    bar = ctk.CTkFrame(parent, fg_color="transparent")
    bar.pack(fill="x", padx=28, pady=(0, 10))
    hint = ctk.CTkLabel(bar, text="", font=F(12), text_color=COLORS["text_muted"], anchor="w")
    hint.pack(side="left", fill="x", expand=True)
    return bar, hint


def table(parent, columns, height=None):
    """Treeview inside a card with a vertical scrollbar. columns = [(key, heading, width, anchor), ...]"""
    wrapper = card(parent)
    inner = ctk.CTkFrame(wrapper, fg_color="transparent")
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    kwargs = {"columns": [c[0] for c in columns], "show": "headings", "selectmode": "browse"}
    if height:
        kwargs["height"] = height
    tree = ttk.Treeview(inner, **kwargs)
    for key, heading, width, anchor in columns:
        tree.heading(key, text=heading, anchor=anchor)
        # Widths act as proportions: columns stretch to fill wide windows and still fit at ~1366px
        tree.column(key, width=int(width * 0.78), anchor=anchor, minwidth=40, stretch=True)
    sb = ctk.CTkScrollbar(inner, command=tree.yview, button_color=COLORS["border"],
                          button_hover_color=COLORS["text_subtle"])
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
    sb.pack(side="right", fill="y", padx=(0, 4), pady=10)
    return wrapper, tree


def style_tree_tags(tree):
    """Row striping and status colours (call after every theme change)."""
    # ttk gives priority to tags configured first, so status tints come before the stripes
    for status, tint in STATUS_TINTS.items():
        tree.tag_configure(status, background=pick(tint))
    tree.tag_configure("odd", background=pick("surface_alt"))
    tree.tag_configure("even", background=pick("surface"))


def insert_row(tree, iid, values, index, status=None):
    tags = ["odd" if index % 2 else "even"]
    if status in STATUS_TINTS:
        tags.append(status)
    tree.insert("", "end", iid=str(iid), values=values, tags=tags)
    # keep the original Python values: Tk would turn "01812345678" into the number 1812345678
    if not hasattr(tree, "raw_rows"):
        tree.raw_rows = {}
    tree.raw_rows[str(iid)] = tuple(values)


STATUS_MARKERS = {"Active": "●", "Expiring Soon": "●", "Expired": "●", "No Subscription": "○"}


def status_text(status, days_left=None):
    marker = STATUS_MARKERS.get(status, "")
    if status == "Expiring Soon" and days_left is not None:
        label = f"Expiring in {days_left}d"
    elif status == "No Subscription":
        label = "No plan"
    else:
        label = status
    return f"{marker} {label}".strip()


def clear_tree(tree):
    tree.delete(*tree.get_children())
    tree.raw_rows = {}


def setup_treeview_style():
    """Configure ttk.Treeview to match the current appearance mode."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    family = font_family()
    bg, fg = pick("surface"), pick("text")
    heading_bg, heading_fg = pick("surface_alt"), pick("text_muted")
    border = pick("border")

    style.configure(
        "Treeview",
        background=bg, foreground=fg, fieldbackground=bg,
        rowheight=34, font=(family, 10), borderwidth=0, relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", pick("primary_soft"))],
        foreground=[("selected", pick("primary"))],
    )
    style.configure(
        "Treeview.Heading",
        background=heading_bg, foreground=heading_fg, relief="flat",
        font=(family, 10, "bold"), padding=(10, 10), borderwidth=0,
    )
    style.map("Treeview.Heading", background=[("active", border)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
