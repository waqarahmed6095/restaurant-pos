from tkinter import ttk

import customtkinter as ctk


class CurrentOrderPanel:
    def __init__(self, parent, colors: dict, on_remove, on_clear, on_print):
        self.frame = ctk.CTkFrame(parent, fg_color=colors["panel"], corner_radius=14)
        self._build(colors, on_remove, on_clear, on_print)

    def _build(self, colors: dict, on_remove, on_clear, on_print):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=0)
        self.frame.rowconfigure(1, weight=1)
        ctk.CTkLabel(
            self.frame,
            text="Current order",
            text_color=colors["ink"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="nw", padx=16, pady=(14, 0))
        self.order_tree = ttk.Treeview(
            self.frame,
            columns=("item", "size", "price", "quantity", "total"),
            show="headings",
            height=5,
            style="Modern.Treeview",
        )
        self.order_tree.heading("item", text="Item")
        self.order_tree.heading("size", text="Size")
        self.order_tree.heading("price", text="Unit Price")
        self.order_tree.heading("quantity", text="Qty")
        self.order_tree.heading("total", text="Total")
        self.order_tree.column("item", width=220, anchor="w")
        self.order_tree.column("size", width=80, anchor="center")
        self.order_tree.column("price", width=90, anchor="center")
        self.order_tree.column("quantity", width=60, anchor="center")
        self.order_tree.column("total", width=90, anchor="center")
        self.order_tree.grid(row=1, column=0, sticky="nsew", padx=12, pady=(4, 6))

        scrollbar = ttk.Scrollbar(
            self.frame, orient="vertical", command=self.order_tree.yview
        )
        self.order_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(4, 6))

        action_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        action_frame.grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12)
        )
        action_frame.columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(
            action_frame,
            text="Remove selected",
            command=on_remove,
            height=36,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(
            action_frame,
            text="Clear order",
            command=on_clear,
            height=36,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkButton(
            action_frame,
            text="PRINT RECEIPT  ->",
            command=on_print,
            height=36,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=2, sticky="ew", padx=(5, 0))
