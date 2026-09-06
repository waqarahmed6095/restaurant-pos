import customtkinter as ctk


class SummaryPanel:
    def __init__(self, parent, colors: dict, callbacks: dict):
        self.frame = ctk.CTkFrame(parent, fg_color=colors["brand"], corner_radius=14)
        self._build(colors, callbacks)

    def _build(self, colors: dict, callbacks: dict):
        ctk.CTkLabel(
            self.frame,
            text="CURRENT TOTAL",
            text_color="#F4DCE0",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 2))
        self.total_label = ctk.CTkLabel(
            self.frame,
            text="Total: Rs 0.00",
            text_color="white",
            font=("Segoe UI", 28, "bold"),
        )
        self.total_label.pack(anchor="w", padx=20, pady=(0, 18))
        for label, callback in (
            ("View session sales", callbacks["session_sales"]),
            ("Sales report", callbacks["sales_report"]),
            ("Sales analytics", callbacks["sales_analytics"]),
            ("End-of-day closing report", callbacks["closing_report"]),
            ("Change PIN", callbacks["change_pin"]),
            ("Printer settings", callbacks["printer_settings"]),
            ("Backup and restore", callbacks["backup_restore"]),
        ):
            ctk.CTkButton(
                self.frame,
                text=label,
                command=callback,
                height=38,
                fg_color="#A94353",
                hover_color=colors["brand_dark"],
                anchor="w",
            ).pack(fill="x", padx=16, pady=(0, 16))
