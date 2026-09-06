import tkinter as tk
from tkinter import ttk

import customtkinter as ctk


class SessionOrdersPanel:
    def __init__(
        self,
        parent,
        colors: dict,
        on_select,
        on_context_menu,
        on_edit,
        on_delete,
    ):
        self.frame = ctk.CTkFrame(parent, fg_color=colors["panel"], corner_radius=14)
        self._build(
            parent,
            colors,
            on_select,
            on_context_menu,
            on_edit,
            on_delete,
        )

    def _build(
        self,
        parent,
        colors: dict,
        on_select,
        on_context_menu,
        on_edit,
        on_delete,
    ):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(2, weight=3)
        self.frame.rowconfigure(3, weight=2)

        ctk.CTkLabel(
            self.frame,
            text="Session orders",
            text_color=colors["ink"],
            font=("Segoe UI", 19, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 2))
        self.summary_label = ctk.CTkLabel(
            self.frame,
            text="0 tickets  ·  Rs 0.00",
            text_color=colors["brand"],
            font=("Segoe UI", 11, "bold"),
        )
        self.summary_label.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 10)
        )

        self.orders_tree = ttk.Treeview(
            self.frame,
            columns=("order", "time", "items", "total"),
            show="headings",
            selectmode="browse",
            height=4,
            style="Modern.Treeview",
        )
        self.orders_tree.heading("order", text="Order")
        self.orders_tree.heading("time", text="Time")
        self.orders_tree.heading("items", text="Items")
        self.orders_tree.heading("total", text="Total")
        self.orders_tree.column("order", width=92, anchor="w", stretch=False)
        self.orders_tree.column("time", width=70, anchor="center", stretch=False)
        self.orders_tree.column("items", width=130, anchor="w")
        self.orders_tree.column("total", width=92, anchor="e", stretch=False)
        self.orders_tree.grid(row=2, column=0, sticky="nsew", padx=(12, 0), pady=6)

        orders_scrollbar = ttk.Scrollbar(
            self.frame, orient="vertical", command=self.orders_tree.yview
        )
        orders_scrollbar.grid(row=2, column=1, sticky="ns", padx=(0, 10), pady=6)
        self.orders_tree.configure(yscrollcommand=orders_scrollbar.set)

        detail_frame = ctk.CTkFrame(
            self.frame, fg_color=colors["soft"], corner_radius=8
        )
        detail_frame.grid(
            row=3, column=0, columnspan=2, sticky="nsew", padx=12, pady=(4, 12)
        )
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(2, weight=1)
        self.detail_header = ctk.CTkLabel(
            detail_frame,
            text="Select an order",
            text_color=colors["ink"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        )
        self.detail_header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 0))
        self.detail_meta = ctk.CTkLabel(
            detail_frame,
            text="",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.detail_meta.grid(row=1, column=0, sticky="ew", padx=12, pady=(1, 5))
        self.detail_tree = ttk.Treeview(
            detail_frame,
            columns=("item", "size", "qty", "total"),
            show="headings",
            height=2,
            style="Modern.Treeview",
        )
        self.detail_tree.heading("item", text="Item")
        self.detail_tree.heading("size", text="Size")
        self.detail_tree.heading("qty", text="Qty")
        self.detail_tree.heading("total", text="Total")
        self.detail_tree.column("item", anchor="w", width=150)
        self.detail_tree.column("size", anchor="center", width=68, stretch=False)
        self.detail_tree.column("qty", anchor="center", width=45, stretch=False)
        self.detail_tree.column("total", anchor="e", width=78, stretch=False)
        self.detail_tree.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        detail_scrollbar = ttk.Scrollbar(
            detail_frame, orient="vertical", command=self.detail_tree.yview
        )
        detail_scrollbar.grid(row=2, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
        self.detail_tree.configure(yscrollcommand=detail_scrollbar.set)

        self.orders_tree.bind("<<TreeviewSelect>>", on_select)
        self.orders_tree.bind("<Button-3>", on_context_menu)
        self.context_menu = tk.Menu(parent, tearoff=0)
        self.context_menu.add_command(label="Edit Order", command=on_edit)
        self.context_menu.add_command(label="Delete Order", command=on_delete)
