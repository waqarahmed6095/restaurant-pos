from tkinter import ttk

import customtkinter as ctk


class OrderEntryPanel:
    def __init__(
        self,
        parent,
        colors: dict,
        category_var,
        item_var,
        size_var,
        quantity_var,
        table_type_var,
        table_number_var,
        categories: list[str],
        on_category_changed,
        on_item_changed,
        on_size_changed,
        on_add,
        on_quantity_change,
        on_table_type_changed,
        on_service_charge_changed,
    ):
        self.frame = ctk.CTkFrame(parent, fg_color=colors["panel"], corner_radius=14)
        self._build(
            colors,
            category_var,
            item_var,
            size_var,
            quantity_var,
            table_type_var,
            table_number_var,
            categories,
            on_category_changed,
            on_item_changed,
            on_size_changed,
            on_add,
            on_quantity_change,
            on_table_type_changed,
            on_service_charge_changed,
        )

    def _build(
        self,
        colors,
        category_var,
        item_var,
        size_var,
        quantity_var,
        table_type_var,
        table_number_var,
        categories,
        on_category_changed,
        on_item_changed,
        on_size_changed,
        on_add,
        on_quantity_change,
        on_table_type_changed,
        on_service_charge_changed,
    ):
        self.frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.frame,
            text="Build an order",
            text_color=colors["ink"],
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 2))
        ctk.CTkLabel(
            self.frame,
            text="Choose a category, item, size, and quantity.",
            text_color=colors["muted"],
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))

        form_frame = ctk.CTkFrame(self.frame, fg_color=colors["soft"], corner_radius=10)
        form_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=2)
        form_frame.columnconfigure(0, weight=1)
        for row, label in ((0, "CATEGORY"), (2, "MENU ITEM"), (4, "SIZE")):
            ctk.CTkLabel(
                form_frame,
                text=label,
                text_color=colors["muted"],
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=row, column=0, sticky="w", padx=12, pady=(12 if row == 0 else 4, 4)
            )

        self.category_menu = ttk.Combobox(
            form_frame,
            textvariable=category_var,
            values=categories,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.category_menu.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.item_menu = ttk.Combobox(
            form_frame,
            textvariable=item_var,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.item_menu.grid(row=3, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.size_menu = ttk.Combobox(
            form_frame,
            textvariable=size_var,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.size_menu.grid(row=5, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.category_menu.bind("<<ComboboxSelected>>", on_category_changed)
        self.item_menu.bind("<<ComboboxSelected>>", on_item_changed)
        self.size_menu.bind("<<ComboboxSelected>>", on_size_changed)
        self.price_label = ctk.CTkLabel(
            form_frame,
            text="Unit price: Rs 0.00",
            text_color=colors["brand"],
            font=("Segoe UI", 13, "bold"),
        )
        self.price_label.grid(row=6, column=0, pady=(2, 12))

        quantity_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        quantity_frame.grid(row=3, column=0, sticky="ew", padx=18, pady=(16, 8))
        ctk.CTkLabel(
            quantity_frame,
            text="Quantity",
            text_color=colors["ink"],
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")
        quantity_stepper = ctk.CTkFrame(
            quantity_frame, fg_color=colors["soft"], corner_radius=8, height=38
        )
        quantity_stepper.pack(side="right")
        quantity_stepper.pack_propagate(False)
        ctk.CTkButton(
            quantity_stepper,
            text="-",
            command=lambda: on_quantity_change(-1),
            width=38,
            height=38,
            corner_radius=7,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        ctk.CTkEntry(
            quantity_stepper,
            textvariable=quantity_var,
            width=44,
            height=38,
            justify="center",
            border_width=0,
            fg_color=colors["soft"],
            text_color=colors["ink"],
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            quantity_stepper,
            text="+",
            command=lambda: on_quantity_change(1),
            width=38,
            height=38,
            corner_radius=7,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            self.frame,
            text="+  ADD TO ORDER",
            command=on_add,
            height=46,
            corner_radius=9,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=4, column=0, sticky="ew", padx=18, pady=(4, 18))

        table_frame = ctk.CTkFrame(
            self.frame, fg_color=colors["panel"], corner_radius=14
        )
        table_frame.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 8))
        table_frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(
            table_frame,
            text="Order destination",
            text_color=colors["ink"],
            font=("Segoe UI", 17, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 4))
        ctk.CTkLabel(
            table_frame,
            text="TYPE",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=3)
        self.table_type_menu = ttk.Combobox(
            table_frame,
            textvariable=table_type_var,
            values=["Indoor", "Outdoor", "Home Delivery"],
            state="readonly",
            style="Modern.TCombobox",
        )
        self.table_type_menu.grid(row=1, column=1, padx=(0, 16), pady=3, sticky="ew")
        self.table_type_menu.bind("<<ComboboxSelected>>", on_table_type_changed)
        ctk.CTkLabel(
            table_frame,
            text="TABLE",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=16, pady=3)
        self.table_number_menu = ttk.Combobox(
            table_frame,
            textvariable=table_number_var,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.table_number_menu.grid(row=2, column=1, padx=(0, 16), pady=3, sticky="ew")
        self.service_charge_check = ctk.CTkCheckBox(
            table_frame,
            text="Add Service Charge",
            variable=on_service_charge_changed[0],
            command=on_service_charge_changed[1],
            text_color=colors["muted"],
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
        )
        self.service_charge_check.grid(
            row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 8)
        )
