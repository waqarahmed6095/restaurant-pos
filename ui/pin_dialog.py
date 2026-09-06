import tkinter as tk

import customtkinter as ctk


def prompt_pin(parent, title: str, colors: dict, confirm: bool = False) -> str | None:
    result = {"pin": None}
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("390x330" if confirm else "390x270")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    ctk.CTkLabel(
        dialog,
        text=title,
        text_color=colors["ink"],
        font=("Segoe UI", 22, "bold"),
    ).pack(anchor="w", padx=28, pady=(24, 2))
    ctk.CTkLabel(
        dialog,
        text="Use 4-12 digits.",
        text_color=colors["muted"],
        font=("Segoe UI", 10),
    ).pack(anchor="w", padx=28, pady=(0, 14))

    pin_var = tk.StringVar()
    confirmation_var = tk.StringVar()
    visible_var = tk.BooleanVar(value=False)
    pin_entry = ctk.CTkEntry(
        dialog,
        textvariable=pin_var,
        show="*",
        height=42,
        placeholder_text="PIN",
        font=("Segoe UI", 16),
    )
    pin_entry.pack(fill="x", padx=28, pady=(0, 8))
    pin_entry.focus_set()

    confirmation_entry = None
    if confirm:
        confirmation_entry = ctk.CTkEntry(
            dialog,
            textvariable=confirmation_var,
            show="*",
            height=42,
            placeholder_text="Confirm PIN",
            font=("Segoe UI", 16),
        )
        confirmation_entry.pack(fill="x", padx=28, pady=(0, 8))

    status = ctk.CTkLabel(dialog, text="", text_color="#B23A48", font=("Segoe UI", 10))
    status.pack(anchor="w", padx=28)

    def toggle_visibility():
        show = "" if visible_var.get() else "*"
        pin_entry.configure(show=show)
        if confirmation_entry:
            confirmation_entry.configure(show=show)

    ctk.CTkCheckBox(
        dialog,
        text="Show PIN",
        variable=visible_var,
        command=toggle_visibility,
        text_color=colors["muted"],
        fg_color=colors["brand"],
        hover_color=colors["brand_dark"],
    ).pack(anchor="w", padx=28, pady=(4, 10))

    def submit():
        pin = pin_var.get()
        if not pin.isdigit() or not 4 <= len(pin) <= 12:
            status.configure(text="PIN must contain 4-12 digits.")
            return
        if confirm and pin != confirmation_var.get():
            status.configure(text="PINs do not match.")
            return
        result["pin"] = pin
        dialog.destroy()

    button = ctk.CTkButton(
        dialog,
        text="Continue",
        command=submit,
        height=42,
        fg_color=colors["brand"],
        hover_color=colors["brand_dark"],
        font=("Segoe UI", 11, "bold"),
    )
    button.pack(fill="x", padx=28, pady=(0, 18))
    dialog.bind("<Return>", lambda _event: submit())
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()
    return result["pin"]
