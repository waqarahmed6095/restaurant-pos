import customtkinter as ctk
from tkinter import ttk


COLORS = {
    "canvas": "#F5F1EA",
    "panel": "#FFFDF9",
    "ink": "#292522",
    "muted": "#766E67",
    "brand": "#8F2434",
    "brand_dark": "#6F1726",
    "line": "#E4DBD1",
    "soft": "#F0E8DF",
}


def configure_theme(window: ctk.CTk) -> dict[str, str]:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)
    window.configure(fg_color=COLORS["canvas"])

    style = ttk.Style(window)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure(
        "Modern.TCombobox",
        padding=10,
        fieldbackground=COLORS["panel"],
        background=COLORS["panel"],
        foreground=COLORS["ink"],
        font=("Segoe UI", 12),
    )
    style.map(
        "Modern.TCombobox",
        fieldbackground=[("readonly", COLORS["panel"])],
        foreground=[("readonly", COLORS["ink"])],
        selectbackground=[("readonly", COLORS["brand"])],
        selectforeground=[("readonly", "white")],
    )
    style.configure(
        "Modern.Treeview",
        rowheight=38,
        background=COLORS["panel"],
        fieldbackground=COLORS["panel"],
        foreground=COLORS["ink"],
        font=("Segoe UI", 11),
    )
    style.configure(
        "Modern.Treeview.Heading",
        background=COLORS["soft"],
        foreground=COLORS["ink"],
        font=("Segoe UI", 11, "bold"),
    )
    style.map(
        "Modern.Treeview",
        background=[("selected", COLORS["brand"])],
        foreground=[("selected", "white")],
    )
    return COLORS.copy()
