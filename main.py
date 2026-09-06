import csv
import json
import os
import shutil
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import customtkinter as ctk

from app_context import AppContext
from controllers.order_controller import OrderController
from controllers.session_controller import SessionController
from domain.order import deserialize_order_items, serialize_order_items
from domain.pricing import get_categories as get_menu_categories
from domain.pricing import \
    get_items_for_category as get_menu_items_for_category
from domain.pricing import get_price_for_item as get_menu_price
from domain.pricing import get_sizes_for_item as get_menu_sizes_for_item
from repositories.auth_repository import hash_pin as repository_hash_pin
from repositories.auth_repository import save_pin as repository_save_pin
from repositories.auth_repository import verify_pin as repository_verify_pin
from repositories.backup_repository import \
    create_backup as repository_create_backup
from repositories.backup_repository import \
    list_backups as repository_list_backups
from repositories.backup_repository import \
    restore_backup as repository_restore_backup
from repositories.menu_repository import \
    load_menu_items as repository_load_menu_items
from repositories.menu_repository import \
    normalize_menu_item as repository_normalize_menu_item
from repositories.menu_repository import \
    save_menu_items as repository_save_menu_items
from repositories.restaurant_repository import \
    load_restaurant as repository_load_restaurant
from repositories.restaurant_repository import \
    save_restaurant as repository_save_restaurant
from repositories.sales_repository import \
    delete_session_order as repository_delete_session_order
from repositories.sales_repository import \
    get_next_order_number as repository_get_next_order_number
from repositories.sales_repository import \
    get_sales_analytics as repository_get_sales_analytics
from repositories.sales_repository import \
    get_sales_report as repository_get_sales_report
from repositories.sales_repository import \
    get_session_id as repository_get_session_id
from repositories.sales_repository import \
    get_session_orders as repository_get_session_orders
from repositories.sales_repository import \
    get_session_sales as repository_get_session_sales
from repositories.sales_repository import \
    record_session_order as repository_record_session_order
from repositories.sales_repository import \
    record_session_sale as repository_record_session_sale
from services.logging_config import configure_logging
from services.printing_service import \
    get_default_printer as service_get_default_printer
from services.printing_service import \
    get_windows_printers as service_get_windows_printers
from services.printing_service import \
    print_with_escpos as service_print_with_escpos
from services.printing_service import \
    print_with_windows_spooler as service_print_with_windows_spooler
from services.receipt_service import \
    build_closing_report_text as service_build_closing_report_text
from services.receipt_service import \
    build_kitchen_slip_text as service_build_kitchen_slip_text
from services.receipt_service import \
    build_receipt_text as service_build_receipt_text
from services.receipt_service import format_currency as service_format_currency
from services.report_service import validate_date_range
from services.validation import validate_contact, validate_image_path
from ui.current_order_panel import CurrentOrderPanel
from ui.dialogs import show_session_sales
from ui.order_entry_panel import OrderEntryPanel
from ui.pin_dialog import prompt_pin
from ui.receipt_preview import load_preview_image
from ui.report_dialogs import (open_closing_report, open_sales_analytics,
                               open_sales_report)
from ui.session_orders_panel import SessionOrdersPanel
from ui.summary_panel import SummaryPanel
from ui.theme import configure_theme

try:
    from PIL import Image, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "Restaurant POS"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RESTAURANT_PATH = DATA_DIR / "restaurant.json"
MENU_ITEMS_PATH = DATA_DIR / "menu_items.json"
SESSION_SALES_PATH = DATA_DIR / "session_sales.json"
PIN_PATH = DATA_DIR / "access.pin"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_FILES = {
    "restaurant.json": RESTAURANT_PATH,
    "menu_items.json": MENU_ITEMS_PATH,
    "session_sales.json": SESSION_SALES_PATH,
    "access.pin": PIN_PATH,
}

RESTAURANT = repository_load_restaurant(RESTAURANT_PATH)
MENU_ITEMS = repository_load_menu_items([], MENU_ITEMS_PATH, include_defaults=False)
APP_CONTEXT = AppContext(
    data_dir=DATA_DIR,
    restaurant_path=RESTAURANT_PATH,
    menu_items_path=MENU_ITEMS_PATH,
    session_sales_path=SESSION_SALES_PATH,
    pin_path=PIN_PATH,
    backup_dir=BACKUP_DIR,
    restaurant=RESTAURANT,
    menu_items=MENU_ITEMS,
)
LOGGER = configure_logging(DATA_DIR)


def create_backup() -> Path:
    return repository_create_backup(BACKUP_DIR, BACKUP_FILES)


def list_backups() -> list[Path]:
    return repository_list_backups(BACKUP_DIR)


def restore_backup(backup_path: str | os.PathLike) -> None:
    repository_restore_backup(backup_path, BACKUP_DIR, BACKUP_FILES)


def get_categories() -> list[str]:
    return get_menu_categories(MENU_ITEMS)


def get_items_for_category(category: str) -> list[str]:
    return get_menu_items_for_category(MENU_ITEMS, category)


def get_sizes_for_item(item_name: str) -> list[str]:
    return get_menu_sizes_for_item(MENU_ITEMS, item_name)


def get_price_for_item(item_name: str, size: str) -> float:
    return get_menu_price(MENU_ITEMS, item_name, size)


def normalize_menu_item(item: dict) -> dict:
    return repository_normalize_menu_item(item)


def load_menu_items(storage_path: str | os.PathLike | None = None) -> list[dict]:
    target_path = storage_path or MENU_ITEMS_PATH
    return repository_load_menu_items(
        MENU_ITEMS, target_path, include_defaults=storage_path is None
    )


def save_menu_items(
    items: list[dict], storage_path: str | os.PathLike | None = None
) -> None:
    repository_save_menu_items(items, storage_path or MENU_ITEMS_PATH)


def format_currency(value: float) -> str:
    return service_format_currency(value)


def build_receipt_text(
    order_items: list[dict],
    table_type: str,
    table_number: str,
    include_service_charge: bool = True,
    order_number: str | None = None,
) -> str:
    return service_build_receipt_text(
        order_items,
        table_type,
        table_number,
        include_service_charge,
        service_charge=RESTAURANT["service_charge"],
        order_number=order_number,
        restaurant_name=RESTAURANT["name"] or "Restaurant",
        restaurant_address=RESTAURANT["address"],
        restaurant_phone=RESTAURANT["phone"],
        restaurant_email=RESTAURANT["email"],
    )


def save_restaurant(restaurant: dict) -> None:
    repository_save_restaurant(restaurant, RESTAURANT_PATH)
    RESTAURANT.clear()
    RESTAURANT.update(restaurant)


def build_kitchen_slip_text(
    order_items: list[dict],
    table_type: str,
    table_number: str,
    order_number: str | None = None,
) -> str:
    return service_build_kitchen_slip_text(
        order_items, table_type, table_number, order_number=order_number
    )


def build_closing_report_text(orders: list[dict], session_id: str) -> str:
    return service_build_closing_report_text(
        orders,
        session_id,
        restaurant_name=RESTAURANT["name"] or "Restaurant",
        service_charge=RESTAURANT["service_charge"],
    )


def get_session_id(now: datetime | None = None) -> str | None:
    return repository_get_session_id(now)


def get_session_sales(
    storage_path: str | os.PathLike | None = None, now: datetime | None = None
) -> float:
    return repository_get_session_sales(storage_path or SESSION_SALES_PATH, now)


def record_session_sale(
    amount: float,
    storage_path: str | os.PathLike | None = None,
    now: datetime | None = None,
) -> float:
    return repository_record_session_sale(
        amount, storage_path or SESSION_SALES_PATH, now
    )


def get_session_orders(
    storage_path: str | os.PathLike | None = None, now: datetime | None = None
) -> list:
    return repository_get_session_orders(storage_path or SESSION_SALES_PATH, now)


def get_sales_report(
    storage_path: str | os.PathLike | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    return repository_get_sales_report(
        storage_path or SESSION_SALES_PATH, start_date, end_date
    )


def get_sales_analytics(
    storage_path: str | os.PathLike | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    return repository_get_sales_analytics(
        storage_path or SESSION_SALES_PATH, start_date, end_date
    )


def get_next_order_number(
    now: datetime | None = None, replace_index: int | None = None
) -> str:
    return repository_get_next_order_number(SESSION_SALES_PATH, now, replace_index)


def record_session_order(
    order: dict,
    storage_path: str | os.PathLike | None = None,
    now: datetime | None = None,
    replace_index: int | None = None,
) -> float:
    return repository_record_session_order(
        order, storage_path or SESSION_SALES_PATH, now, replace_index
    )


def delete_session_order(
    index: int,
    storage_path: str | os.PathLike | None = None,
    now: datetime | None = None,
) -> float:
    return repository_delete_session_order(
        index, storage_path or SESSION_SALES_PATH, now
    )


def hash_pin(pin: str) -> str:
    return repository_hash_pin(pin)


def verify_pin(pin: str, pin_path: str | os.PathLike = PIN_PATH) -> bool:
    return repository_verify_pin(pin, pin_path)


def save_pin(pin: str, pin_path: str | os.PathLike = PIN_PATH) -> None:
    repository_save_pin(pin, pin_path)


class RestaurantPOS(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.after(0, self.start_application)

    def start_application(self):
        if not RESTAURANT["name"]:
            self.deiconify()
            self.state("normal")
            self.update()
            self.configure_restaurant()
            return
        self.finish_application()

    def finish_application(self):
        self.title(f'{RESTAURANT["name"]} - POS')
        self.authenticated = self.authenticate_user()
        if not self.authenticated:
            self.quit()
            return
        try:
            create_backup()
        except OSError as exc:
            print(f"Automatic backup failed: {exc}")
        self.apply_window_icon()
        self.resizable(True, True)
        try:
            self.state("zoomed")
        except Exception:
            pass

        self.order_controller = OrderController()
        self.order_items = self.order_controller.items
        self.session_controller = SessionController(
            get_session_orders, delete_session_order
        )
        self.editing_session_order_index = None
        self.categories = get_categories()
        self.selected_category = tk.StringVar(
            value=self.categories[0] if self.categories else ""
        )
        self.selected_item = tk.StringVar()
        self.selected_size = tk.StringVar()
        self.quantity = tk.IntVar(value=1)
        self.table_type = tk.StringVar(value="Indoor")
        self.table_number = tk.StringVar(value="1")
        self.include_service_charge = tk.BooleanVar(value=True)
        self.create_widgets()
        self.update_session_sales_label()
        self.after(100, self.maximize_window)

    def configure_restaurant(self):
        setup_window = self
        setup_window.title("Restaurant setup")
        screen_width = setup_window.winfo_screenwidth()
        screen_height = setup_window.winfo_screenheight()
        setup_width = min(900, max(700, screen_width - 100))
        setup_height = min(650, max(540, screen_height - 120))
        setup_window.geometry(f"{setup_width}x{setup_height}")
        setup_window.minsize(700, 540)
        setup_window.resizable(True, True)
        colors = configure_theme(setup_window)

        values = {
            "name": tk.StringVar(),
            "address": tk.StringVar(),
            "phone": tk.StringVar(),
            "email": tk.StringVar(),
            "logo_path": tk.StringVar(),
            "app_icon_path": tk.StringVar(),
            "footer_path": tk.StringVar(),
            "printer_name": tk.StringVar(),
            "service_charge": tk.StringVar(value="0"),
            "indoor_tables": tk.StringVar(value="10"),
            "outdoor_tables": tk.StringVar(value="25"),
            "menu_path": tk.StringVar(),
        }

        setup_window.grid_columnconfigure(0, weight=1)
        setup_window.grid_columnconfigure(1, weight=2)
        setup_window.grid_rowconfigure(0, weight=1)

        welcome_panel = ctk.CTkFrame(
            setup_window, fg_color=colors["brand"], corner_radius=0
        )
        welcome_panel.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(
            welcome_panel,
            text="RESTAURANT\nPOS",
            text_color="white",
            font=("Segoe UI", 30, "bold"),
            justify="left",
        ).pack(anchor="w", padx=34, pady=(54, 18))
        ctk.CTkLabel(
            welcome_panel,
            text="Set up the identity\nof this installation.",
            text_color="#F6DDE1",
            font=("Segoe UI", 16),
            justify="left",
        ).pack(anchor="w", padx=34)
        ctk.CTkLabel(
            welcome_panel,
            text="Your menu, receipts, branding,\nand sales data stay with this restaurant.",
            text_color="#F3C8CF",
            font=("Segoe UI", 11),
            justify="left",
        ).pack(anchor="w", padx=34, pady=(260, 0))

        form_panel = ctk.CTkFrame(
            setup_window, fg_color=colors["panel"], corner_radius=0
        )
        form_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        form_panel.grid_columnconfigure(0, weight=1)
        form_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            form_panel,
            text="Restaurant setup",
            text_color=colors["ink"],
            font=("Segoe UI", 25, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=34, pady=(30, 2))
        ctk.CTkLabel(
            form_panel,
            text="Add the details that appear across your POS and receipts.",
            text_color=colors["muted"],
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=34, pady=(0, 16))

        def add_field(row, label, key, column=0, columnspan=1):
            ctk.CTkLabel(
                form_panel,
                text=label.upper(),
                text_color=colors["muted"],
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=row,
                column=column,
                columnspan=columnspan,
                sticky="w",
                padx=(34 if column == 0 else 10, 10),
                pady=(0, 5),
            )
            entry = ctk.CTkEntry(
                form_panel,
                textvariable=values[key],
                height=38,
                border_width=1,
                border_color=colors["line"],
                fg_color=colors["canvas"],
                text_color=colors["ink"],
            )
            entry.grid(
                row=row + 1,
                column=column,
                columnspan=columnspan,
                sticky="ew",
                padx=(34 if column == 0 else 10, 10),
                pady=(0, 8),
            )
            return entry

        add_field(2, "Restaurant name", "name", columnspan=2)
        add_field(4, "Address", "address", columnspan=2)
        add_field(6, "Phone", "phone")
        add_field(6, "Email", "email", column=1)
        add_field(8, "Service charge", "service_charge")

        def choose_file(key):
            if key == "menu_path":
                filetypes = [("Menu JSON", "*.json"), ("All files", "*.*")]
            elif key == "app_icon_path":
                filetypes = [("Windows icon", "*.ico")]
            else:
                filetypes = [
                    ("Image files", "*.png *.jpg *.jpeg"),
                    ("All files", "*.*"),
                ]
            selected = filedialog.askopenfilename(
                parent=setup_window,
                title=f"Choose {key.replace('_', ' ')}",
                filetypes=filetypes,
            )
            if selected:
                values[key].set(selected)
                if key == "app_icon_path":
                    self.apply_window_icon(selected)

        asset_fields = ctk.CTkFrame(form_panel, fg_color="transparent")
        asset_fields.grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=34, pady=(0, 8)
        )
        asset_fields.grid_columnconfigure(0, weight=1)
        asset_fields.grid_columnconfigure(1, weight=1)
        asset_fields.grid_columnconfigure(2, weight=1)
        for column, key in enumerate(("logo_path", "footer_path", "menu_path")):
            ctk.CTkLabel(
                asset_fields,
                text=key.replace("_", " ").upper(),
                text_color=colors["muted"],
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=0,
                column=column,
                sticky="w",
                padx=(0 if column == 0 else 10, 10),
                pady=(0, 5),
            )
            asset_row = ctk.CTkFrame(asset_fields, fg_color="transparent")
            asset_row.grid(
                row=1, column=column, sticky="ew", padx=(0 if column == 0 else 10, 10)
            )
            asset_row.grid_columnconfigure(0, weight=1)
            ctk.CTkEntry(
                asset_row,
                textvariable=values[key],
                height=38,
                border_width=1,
                border_color=colors["line"],
                fg_color=colors["canvas"],
                text_color=colors["ink"],
            ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
            ctk.CTkButton(
                asset_row,
                text="Browse",
                command=lambda selected_key=key: choose_file(selected_key),
                width=72,
                height=38,
                fg_color=colors["soft"],
                hover_color=colors["line"],
                text_color=colors["ink"],
            ).grid(row=0, column=1)

        ctk.CTkLabel(
            asset_fields,
            text="APP ICON (.ICO)",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 5))
        icon_row = ctk.CTkFrame(asset_fields, fg_color="transparent")
        icon_row.grid(row=3, column=0, columnspan=3, sticky="ew")
        icon_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(
            icon_row,
            textvariable=values["app_icon_path"],
            height=38,
            border_width=1,
            border_color=colors["line"],
            fg_color=colors["canvas"],
            text_color=colors["ink"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            icon_row,
            text="Browse",
            command=lambda: choose_file("app_icon_path"),
            width=72,
            height=38,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            asset_fields,
            text="PRINTER",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 5))
        printer_values = self.get_windows_printers()
        printer_row = ctk.CTkFrame(asset_fields, fg_color="transparent")
        printer_row.grid(row=5, column=0, columnspan=3, sticky="ew")
        printer_row.grid_columnconfigure(0, weight=1)
        printer_menu = ttk.Combobox(
            printer_row,
            textvariable=values["printer_name"],
            values=printer_values,
            state="normal",
        )
        printer_menu.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        if printer_values:
            default_printer = self.get_default_printer()
            values["printer_name"].set(default_printer or printer_values[0])
        ctk.CTkButton(
            printer_row,
            text="Refresh",
            command=lambda: printer_menu.configure(values=self.get_windows_printers()),
            width=82,
            height=38,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).grid(row=0, column=1)

        table_count_frame = ctk.CTkFrame(form_panel, fg_color="transparent")
        table_count_frame.grid(row=8, column=1, sticky="ew", padx=(10, 34), pady=(0, 8))
        table_count_frame.grid_columnconfigure(0, weight=1)
        table_count_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            table_count_frame,
            text="INDOOR TABLES",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 5))
        ctk.CTkEntry(
            table_count_frame,
            textvariable=values["indoor_tables"],
            height=38,
            border_width=1,
            border_color=colors["line"],
            fg_color=colors["canvas"],
            text_color=colors["ink"],
        ).grid(row=1, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(
            table_count_frame,
            text="OUTDOOR TABLES",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=(6, 0), pady=(0, 5))
        ctk.CTkEntry(
            table_count_frame,
            textvariable=values["outdoor_tables"],
            height=38,
            border_width=1,
            border_color=colors["line"],
            fg_color=colors["canvas"],
            text_color=colors["ink"],
        ).grid(row=1, column=1, sticky="ew", padx=(6, 0))

        def submit():
            name = values["name"].get().strip()
            address = values["address"].get().strip()
            phone = values["phone"].get().strip()
            email = values["email"].get().strip()
            if not name:
                messagebox.showerror(
                    "Restaurant setup",
                    "Restaurant name is required.",
                    parent=setup_window,
                )
                return
            if len(name) > 100:
                messagebox.showerror(
                    "Restaurant setup",
                    "Restaurant name must be 100 characters or fewer.",
                    parent=setup_window,
                )
                return
            if not address:
                messagebox.showerror(
                    "Restaurant setup", "Address is required.", parent=setup_window
                )
                return
            if len(address) > 200:
                messagebox.showerror(
                    "Restaurant setup",
                    "Address must be 200 characters or fewer.",
                    parent=setup_window,
                )
                return
            contact_error = validate_contact(phone, email)
            if contact_error:
                messagebox.showerror(
                    "Restaurant setup", contact_error, parent=setup_window
                )
                return
            try:
                service_charge = max(0.0, float(values["service_charge"].get() or 0))
                indoor_tables = max(0, int(values["indoor_tables"].get() or 0))
                outdoor_tables = max(0, int(values["outdoor_tables"].get() or 0))
                if (
                    service_charge > 1_000_000
                    or indoor_tables > 500
                    or outdoor_tables > 500
                ):
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Restaurant setup",
                    "Use valid non-negative values (table counts up to 500).",
                    parent=setup_window,
                )
                return
            for key, label, extensions in (
                ("logo_path", "Logo", {".png", ".jpg", ".jpeg"}),
                ("footer_path", "Footer image", {".png", ".jpg", ".jpeg"}),
            ):
                image_path = values[key].get().strip()
                image_error = validate_image_path(image_path, extensions, label)
                if image_error:
                    messagebox.showerror(
                        "Restaurant setup",
                        image_error,
                        parent=setup_window,
                    )
                    return
            icon_path = values["app_icon_path"].get().strip()
            if icon_path and (
                not Path(icon_path).is_file()
                or Path(icon_path).suffix.lower() != ".ico"
            ):
                messagebox.showerror(
                    "Restaurant setup",
                    "Choose a valid Windows .ico app icon.",
                    parent=setup_window,
                )
                return
            menu_path = values["menu_path"].get().strip()
            imported_items = None
            if menu_path:
                try:
                    menu_file = Path(menu_path)
                    if not menu_file.is_file() or menu_file.suffix.lower() != ".json":
                        raise ValueError
                    menu_data = json.loads(menu_file.read_text(encoding="utf-8"))
                    if not isinstance(menu_data, list) or not all(
                        isinstance(item, dict) for item in menu_data
                    ):
                        raise ValueError
                    imported_items = []
                    for item in menu_data:
                        if not all(
                            str(item.get(key, "")).strip()
                            for key in ("category", "name", "size")
                        ):
                            raise ValueError
                        price = float(item.get("price"))
                        if price < 0:
                            raise ValueError
                        imported_items.append(normalize_menu_item(item))
                except (
                    OSError,
                    UnicodeError,
                    json.JSONDecodeError,
                    TypeError,
                    ValueError,
                ):
                    messagebox.showerror(
                        "Restaurant setup",
                        "Choose a valid menu JSON file with category, name, size, and non-negative price for every item.",
                        parent=setup_window,
                    )
                    return
            restaurant = {
                key: value.get().strip()
                for key, value in values.items()
                if key
                not in {
                    "service_charge",
                    "indoor_tables",
                    "outdoor_tables",
                    "menu_path",
                }
            }
            restaurant["service_charge"] = service_charge
            restaurant["indoor_tables"] = indoor_tables
            restaurant["outdoor_tables"] = outdoor_tables
            save_restaurant(restaurant)
            if imported_items is not None:
                repository_save_menu_items(imported_items, MENU_ITEMS_PATH)
                MENU_ITEMS[:] = imported_items
            for child in setup_window.winfo_children():
                child.destroy()
            self.finish_application()

        ctk.CTkButton(
            form_panel,
            text="Save and continue",
            command=submit,
            height=44,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=12, column=0, columnspan=2, sticky="ew", padx=34, pady=(4, 30))
        setup_window.bind("<Return>", lambda _event: submit())

    def authenticate_user(self) -> bool:
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()
        colors = configure_theme(self)
        if PIN_PATH.exists():
            pin = prompt_pin(self, "Staff login", colors)
            if not pin or not verify_pin(pin):
                messagebox.showerror("Staff login", "Incorrect PIN.")
                return False
        else:
            pin = prompt_pin(self, "Create PIN", colors, confirm=True)
            if not pin:
                return False
            save_pin(pin)
        return True

    def change_pin(self):
        colors = configure_theme(self)
        current_pin = prompt_pin(self, "Current PIN", colors)
        if not current_pin or not verify_pin(current_pin):
            messagebox.showerror("Change PIN", "Current PIN is incorrect.", parent=self)
            return

        new_pin = prompt_pin(self, "New PIN", colors, confirm=True)
        if not new_pin:
            return

        save_pin(new_pin)
        messagebox.showinfo("Change PIN", "PIN changed successfully.", parent=self)

    def maximize_window(self):
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

    def change_quantity(self, amount: int):
        try:
            current_quantity = int(self.quantity.get())
        except (tk.TclError, ValueError):
            current_quantity = 1
        self.quantity.set(max(1, min(20, current_quantity + amount)))

    def create_widgets(self):
        self.logo_image = self.load_logo_image()
        colors = configure_theme(self)

        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=6)
        self.columnconfigure(2, weight=2)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(2, weight=2)

        top_frame = ctk.CTkFrame(self, fg_color=colors["panel"], corner_radius=14)
        top_frame.grid(
            row=0, column=0, columnspan=3, sticky="ew", padx=18, pady=(16, 8)
        )
        top_frame.columnconfigure(1, weight=1)
        if self.logo_image:
            ctk.CTkLabel(top_frame, image=self.logo_image, text="").grid(
                row=0, column=0, padx=(18, 8), pady=10
            )
        header_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        header_frame.grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkLabel(
            header_frame,
            text=RESTAURANT["name"].upper(),
            text_color=colors["brand"],
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header_frame,
            text=f'Order desk  /  {RESTAURANT["address"]}',
            text_color=colors["muted"],
            font=("Segoe UI", 12),
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            top_frame,
            text="LIVE SERVICE",
            text_color=colors["brand"],
            fg_color=colors["soft"],
            corner_radius=8,
            padx=12,
            pady=6,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=2, padx=18)

        order_entry_panel = OrderEntryPanel(
            self,
            colors,
            self.selected_category,
            self.selected_item,
            self.selected_size,
            self.quantity,
            self.table_type,
            self.table_number,
            self.categories,
            self.update_items,
            self.update_sizes,
            lambda _event: self.update_price(),
            self.add_item_to_order,
            self.change_quantity,
            self.update_table_numbers,
            (self.include_service_charge, self.refresh_order_view),
        )
        order_entry_panel.frame.grid(
            row=1, column=0, sticky="nsew", padx=(18, 8), pady=(8, 10)
        )
        self.category_menu = order_entry_panel.category_menu
        self.item_menu = order_entry_panel.item_menu
        self.size_menu = order_entry_panel.size_menu
        self.price_label = order_entry_panel.price_label
        self.table_type_menu = order_entry_panel.table_type_menu
        self.table_number_menu = order_entry_panel.table_number_menu
        self.service_charge_check = order_entry_panel.service_charge_check
        self.update_items()
        self.update_table_numbers()

        middle_container = ctk.CTkFrame(self, fg_color="transparent")
        middle_container.grid(
            row=1, column=1, rowspan=2, sticky="nsew", padx=(10, 4), pady=(8, 18)
        )
        middle_container.columnconfigure(0, weight=1)
        middle_container.rowconfigure(0, weight=0)
        middle_container.rowconfigure(1, weight=1)

        summary_panel = SummaryPanel(
            self,
            colors,
            callbacks={
                "session_sales": self.display_session_sales,
                "sales_report": self.display_sales_report,
                "sales_analytics": self.display_sales_analytics,
                "closing_report": self.display_closing_report,
                "change_pin": self.change_pin,
                "printer_settings": self.open_printer_settings,
                "backup_restore": self.open_backup_restore,
            },
        )
        summary_panel.frame.grid(
            row=1, column=2, rowspan=2, sticky="nsew", padx=(4, 18), pady=(8, 18)
        )
        self.total_label = summary_panel.total_label
        ctk.CTkButton(
            middle_container,
            text="Manage menu",
            command=self.open_menu_manager,
            height=38,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            text_color="white",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=2, column=0, sticky="ew", pady=(10, 0))

        session_orders_panel = SessionOrdersPanel(
            middle_container,
            colors,
            on_select=lambda _event: self.show_selected_order_details(),
            on_context_menu=self.show_session_order_context_menu,
            on_edit=self.edit_selected_session_order,
            on_delete=self.delete_selected_session_order,
        )
        session_orders_panel.frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.session_orders_listbox = session_orders_panel.orders_tree
        self.session_summary_label = session_orders_panel.summary_label
        self.order_detail_header = session_orders_panel.detail_header
        self.order_detail_meta = session_orders_panel.detail_meta
        self.order_detail_tree = session_orders_panel.detail_tree
        self.session_order_context_menu = session_orders_panel.context_menu

        current_order_panel = CurrentOrderPanel(
            middle_container,
            colors,
            on_remove=self.remove_selected_item,
            on_clear=self.clear_order,
            on_print=self.print_slip,
        )
        current_order_panel.frame.grid(row=1, column=0, sticky="nsew")
        self.order_tree = current_order_panel.order_tree

    def load_logo_image(self):
        logo_path = RESTAURANT["logo_path"]
        if not PIL_AVAILABLE or not logo_path or not os.path.exists(logo_path):
            return None
        try:
            img = Image.open(logo_path)
            img.thumbnail(
                (110, 78),
                (
                    Image.Resampling.LANCZOS
                    if hasattr(Image, "Resampling")
                    else Image.ANTIALIAS
                ),
            )
            return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        except Exception:
            return None

    def apply_window_icon(self, logo_path: str | os.PathLike | None = None):
        icon_path = logo_path or RESTAURANT.get("app_icon_path", "")
        if icon_path and os.path.isfile(icon_path):
            try:
                self.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass
        window_icon = self.load_window_icon(icon_path)
        if window_icon:
            self.window_icon = window_icon
            self.iconphoto(True, window_icon)

    def load_window_icon(self, logo_path: str | os.PathLike | None = None):
        logo_path = logo_path or RESTAURANT["logo_path"]
        if not PIL_AVAILABLE or not logo_path or not os.path.exists(logo_path):
            return None
        try:
            img = Image.open(logo_path).convert("RGBA")
            img.thumbnail(
                (64, 64),
                (
                    Image.Resampling.LANCZOS
                    if hasattr(Image, "Resampling")
                    else Image.ANTIALIAS
                ),
            )
            return ImageTk.PhotoImage(img, master=self)
        except Exception:
            return None

    def update_items(self, *_):
        items = get_items_for_category(self.selected_category.get())
        self.item_menu["values"] = items
        if not items:
            self.selected_item.set("")
            self.size_menu["values"] = []
            self.selected_size.set("")
            self.price_label.configure(text="Unit Price: Rs 0.00")
            return
        self.selected_item.set(items[0])
        self.update_sizes()

    def update_sizes(self, *_):
        sizes = get_sizes_for_item(self.selected_item.get())
        self.size_menu["values"] = sizes
        if not sizes:
            self.selected_size.set("")
            self.price_label.configure(text="Unit Price: Rs 0.00")
            return
        self.selected_size.set(sizes[0])
        self.update_price()

    def update_price(self):
        price = get_price_for_item(self.selected_item.get(), self.selected_size.get())
        self.price_label.configure(text=f"Unit Price: {format_currency(price)}")

    def refresh_menu_controls(self):
        global MENU_ITEMS
        MENU_ITEMS[:] = load_menu_items()
        self.categories = get_categories()
        if hasattr(self, "category_menu"):
            self.category_menu["values"] = self.categories
        if not self.categories:
            self.selected_category.set("")
            self.selected_item.set("")
            self.selected_size.set("")
            self.price_label.configure(text="Unit Price: Rs 0.00")
            return

        if self.selected_category.get() not in self.categories:
            self.selected_category.set(self.categories[0])
        self.update_items()

    def open_menu_manager(self):
        menu_window = tk.Toplevel(self)
        menu_window.title("Menu Manager")
        menu_window.geometry(
            f"{min(1000, max(760, menu_window.winfo_screenwidth() - 120))}x"
            f"{min(760, max(560, menu_window.winfo_screenheight() - 140))}"
        )
        menu_window.minsize(720, 520)
        menu_window.resizable(True, True)
        menu_window.transient(self)
        menu_window.grab_set()
        colors = configure_theme(self)
        menu_window.configure(bg=colors["canvas"])

        menu_window.columnconfigure(0, weight=1)
        menu_window.rowconfigure(2, weight=1)

        header_frame = ctk.CTkFrame(
            menu_window, fg_color=colors["panel"], corner_radius=12
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        ctk.CTkLabel(
            header_frame,
            text="Menu manager",
            text_color=colors["ink"],
            font=("Segoe UI", 21, "bold"),
        ).pack(anchor="w", padx=18, pady=(14, 0))
        ctk.CTkLabel(
            header_frame,
            text="Add new dishes or update pricing without leaving the order desk.",
            text_color=colors["muted"],
            font=("Segoe UI", 11),
        ).pack(anchor="w", padx=18, pady=(2, 14))

        form_frame = ctk.CTkFrame(
            menu_window, fg_color=colors["panel"], corner_radius=12
        )
        form_frame.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        form_frame.columnconfigure(1, weight=1)
        ctk.CTkLabel(
            form_frame,
            text="ITEM DETAILS",
            text_color=colors["brand"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 8))

        self.menu_manager_name = tk.StringVar()
        self.menu_manager_category = tk.StringVar()
        self.menu_manager_size = tk.StringVar()
        self.menu_manager_price = tk.StringVar()

        ctk.CTkLabel(
            form_frame,
            text="Name",
            text_color=colors["muted"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=5)
        ctk.CTkEntry(
            form_frame,
            textvariable=self.menu_manager_name,
            height=36,
            border_width=1,
            border_color=colors["line"],
            fg_color=colors["canvas"],
            text_color=colors["ink"],
        ).grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=5)

        ctk.CTkLabel(
            form_frame,
            text="Category",
            text_color=colors["muted"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=16, pady=5)
        self.menu_manager_category_menu = ttk.Combobox(
            form_frame,
            textvariable=self.menu_manager_category,
            values=self.get_menu_manager_categories(),
            state="readonly",
            style="Modern.TCombobox",
        )
        self.menu_manager_category_menu.grid(
            row=2, column=1, sticky="ew", padx=(0, 16), pady=5
        )
        self.menu_manager_category_menu.bind(
            "<<ComboboxSelected>>", self.handle_menu_manager_category
        )

        ctk.CTkLabel(
            form_frame,
            text="Size",
            text_color=colors["muted"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=3, column=0, sticky="w", padx=16, pady=5)
        self.menu_manager_size_menu = ttk.Combobox(
            form_frame,
            textvariable=self.menu_manager_size,
            values=self.get_menu_manager_sizes(),
            state="readonly",
            style="Modern.TCombobox",
        )
        self.menu_manager_size_menu.grid(
            row=3, column=1, sticky="ew", padx=(0, 16), pady=5
        )
        self.menu_manager_size_menu.bind(
            "<<ComboboxSelected>>", self.handle_menu_manager_size
        )

        ctk.CTkLabel(
            form_frame,
            text="Price (Rs)",
            text_color=colors["muted"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=4, column=0, sticky="w", padx=16, pady=5)
        ctk.CTkEntry(
            form_frame,
            textvariable=self.menu_manager_price,
            height=36,
            border_width=1,
            border_color=colors["line"],
            fg_color=colors["canvas"],
            text_color=colors["ink"],
        ).grid(row=4, column=1, sticky="ew", padx=(0, 16), pady=5)

        ctk.CTkButton(
            form_frame,
            text="+  ADD MENU ITEM",
            command=self.add_menu_item_from_window,
            height=38,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=5, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 16))

        tree_frame = ctk.CTkFrame(
            menu_window, fg_color=colors["panel"], corner_radius=12
        )
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 16))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=0)
        ctk.CTkLabel(
            tree_frame,
            text="Current menu",
            text_color=colors["ink"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(
            tree_frame,
            text="Select an item to load it into the form for editing.",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 8))
        tree_frame.rowconfigure(2, weight=1)

        self.menu_tree = ttk.Treeview(
            tree_frame,
            columns=("category", "name", "size", "price"),
            show="headings",
            height=14,
        )
        self.menu_tree.heading("category", text="Category")
        self.menu_tree.heading("name", text="Name")
        self.menu_tree.heading("size", text="Size")
        self.menu_tree.heading("price", text="Price")
        self.menu_tree.column("category", width=140, anchor="w")
        self.menu_tree.column("name", width=220, anchor="w")
        self.menu_tree.column("size", width=100, anchor="center")
        self.menu_tree.column("price", width=100, anchor="center")
        self.menu_tree.grid(row=2, column=0, sticky="nsew", padx=(12, 0), pady=8)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.menu_tree.yview
        )
        scrollbar.grid(row=2, column=1, sticky="ns", padx=(0, 12), pady=8)
        self.menu_tree.configure(yscrollcommand=scrollbar.set)

        button_row = ttk.Frame(tree_frame)
        button_row.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 14)
        )
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)

        self.menu_tree.bind(
            "<<TreeviewSelect>>", self.load_selected_menu_item_into_form
        )

        edit_button = ctk.CTkButton(
            button_row,
            text="EDIT SELECTED",
            command=self.edit_selected_menu_item_from_window,
            height=38,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 11, "bold"),
        )
        edit_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        remove_button = ctk.CTkButton(
            button_row,
            text="REMOVE SELECTED",
            command=self.remove_selected_menu_item_from_window,
            height=38,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
            font=("Segoe UI", 11, "bold"),
        )
        remove_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.refresh_menu_manager_tree()

    def get_menu_manager_categories(self):
        return get_categories() + ["Add new category..."]

    def get_menu_manager_sizes(self):
        sizes = sorted({item["size"] for item in MENU_ITEMS if item["size"]})
        return sizes + ["Add new size..."]

    def handle_menu_manager_category(self, *_):
        if self.menu_manager_category.get() != "Add new category...":
            return
        category = simpledialog.askstring(
            "New category", "Enter the new category name:", parent=self
        )
        if category and category.strip():
            category = category.strip()
            values = self.get_menu_manager_categories()
            if category not in values:
                values.insert(-1, category)
            self.menu_manager_category_menu["values"] = values
            self.menu_manager_category.set(category)
        else:
            self.menu_manager_category.set("")

    def handle_menu_manager_size(self, *_):
        if self.menu_manager_size.get() != "Add new size...":
            return
        size = simpledialog.askstring("New size", "Enter the new size:", parent=self)
        if size and size.strip():
            size = size.strip()
            values = self.get_menu_manager_sizes()
            if size not in values:
                values.insert(-1, size)
            self.menu_manager_size_menu["values"] = values
            self.menu_manager_size.set(size)
        else:
            self.menu_manager_size.set("")

    def refresh_menu_manager_tree(self):
        if not hasattr(self, "menu_tree"):
            return
        for row in self.menu_tree.get_children():
            self.menu_tree.delete(row)

        sorted_items = sorted(
            enumerate(MENU_ITEMS),
            key=lambda entry: (
                entry[1]["category"].casefold(),
                entry[1]["name"].casefold(),
                entry[1]["size"].casefold(),
            ),
        )
        for idx, item in sorted_items:
            self.menu_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    item["category"],
                    item["name"],
                    item["size"],
                    format_currency(item["price"]),
                ),
            )

    def load_selected_menu_item_into_form(self, *_):
        selection = self.menu_tree.selection()
        if not selection:
            return
        item = MENU_ITEMS[int(selection[0])]
        self.menu_manager_name.set(item["name"])
        self.menu_manager_category.set(item["category"])
        self.menu_manager_size.set(item["size"])
        self.menu_manager_price.set(str(item["price"]))

    def edit_selected_menu_item_from_window(self):
        selection = self.menu_tree.selection()
        if not selection:
            messagebox.showinfo("Edit menu item", "Please select a menu item to edit.")
            return

        name = self.menu_manager_name.get().strip()
        category = self.menu_manager_category.get().strip()
        size = self.menu_manager_size.get().strip()
        price_text = self.menu_manager_price.get().strip()
        if not name or not category or not size or not price_text:
            messagebox.showerror(
                "Edit menu item", "Please fill in all menu item fields."
            )
            return
        try:
            price = float(price_text)
        except ValueError:
            messagebox.showerror(
                "Edit menu item", "Please enter a valid numeric price."
            )
            return
        if price < 0:
            messagebox.showerror("Edit menu item", "Price cannot be negative.")
            return

        index = int(selection[0])
        duplicate = any(
            idx != index
            and item["name"].casefold() == name.casefold()
            and item["category"].casefold() == category.casefold()
            and item["size"].casefold() == size.casefold()
            for idx, item in enumerate(MENU_ITEMS)
        )
        if duplicate:
            messagebox.showerror(
                "Edit menu item",
                "Another menu item has the same category, name, and size.",
            )
            return

        MENU_ITEMS[index] = {
            "category": category,
            "name": name,
            "size": size,
            "price": price,
        }
        save_menu_items(MENU_ITEMS)
        self.refresh_menu_controls()
        self.refresh_menu_manager_tree()
        messagebox.showinfo("Edit menu item", "Menu item updated successfully.")

    def add_menu_item_from_window(self):
        name = self.menu_manager_name.get().strip()
        category = self.menu_manager_category.get().strip()
        size = self.menu_manager_size.get().strip()
        price_text = self.menu_manager_price.get().strip()

        if not name or not category or not size or not price_text:
            messagebox.showerror(
                "Add menu item", "Please fill in all menu item fields."
            )
            return

        try:
            price = float(price_text)
        except ValueError:
            messagebox.showerror("Add menu item", "Please enter a valid numeric price.")
            return

        if price < 0:
            messagebox.showerror("Add menu item", "Price cannot be negative.")
            return

        duplicate = any(
            item["name"].lower() == name.lower()
            and item["category"].lower() == category.lower()
            and item["size"].lower() == size.lower()
            for item in MENU_ITEMS
        )
        if duplicate:
            if not messagebox.askyesno(
                "Duplicate menu item",
                "A menu item with the same category, name, and size already exists. Add anyway?",
            ):
                return

        MENU_ITEMS.append(
            {"category": category, "name": name, "size": size, "price": price}
        )
        save_menu_items(MENU_ITEMS)
        self.refresh_menu_controls()
        self.refresh_menu_manager_tree()
        self.menu_manager_name.set("")
        self.menu_manager_category.set("")
        self.menu_manager_size.set("")
        self.menu_manager_price.set("")
        messagebox.showinfo("Add menu item", "Menu item added successfully.")

    def remove_selected_menu_item_from_window(self):
        if not hasattr(self, "menu_tree"):
            return
        selection = self.menu_tree.selection()
        if not selection:
            messagebox.showinfo(
                "Remove menu item", "Please select a menu item to remove."
            )
            return

        index = int(selection[0])
        item = MENU_ITEMS[index]
        if not messagebox.askyesno(
            "Remove menu item",
            f"Remove {item['name']} ({item['size']}) from {item['category']}?",
        ):
            return

        MENU_ITEMS.pop(index)
        save_menu_items(MENU_ITEMS)
        self.refresh_menu_controls()
        self.refresh_menu_manager_tree()
        messagebox.showinfo("Remove menu item", "Menu item removed successfully.")

    def update_table_numbers(self, *_):
        if self.table_type.get() == "Home Delivery":
            self.table_number_menu["values"] = []
            self.table_number.set("")
            self.table_number_menu.config(state="disabled")
        else:
            if self.table_type.get() == "Outdoor":
                table_count = RESTAURANT["outdoor_tables"]
            else:
                table_count = RESTAURANT["indoor_tables"]
            numbers = [str(number) for number in range(1, table_count + 1)]
            if not numbers:
                self.table_number.set("")
                self.table_number_menu["values"] = []
                self.table_number_menu.config(state="disabled")
                return

            self.table_number_menu.config(state="readonly")
            self.table_number_menu["values"] = numbers
            if self.table_number.get() not in numbers:
                self.table_number.set(numbers[0])

    def add_item_to_order(self):
        item_name = self.selected_item.get()
        size = self.selected_size.get()
        qty = self.quantity.get()
        if not item_name or not size:
            messagebox.showinfo("Add item", "Please select a menu item and size first.")
            return
        if qty <= 0:
            messagebox.showerror(
                "Invalid quantity", "Please enter a quantity of 1 or more."
            )
            return

        price = get_price_for_item(item_name, size)
        self.order_controller.add_item(item_name, size, qty, price)
        self.refresh_order_view()

    def remove_selected_item(self):
        selected = self.order_tree.selection()
        if not selected:
            messagebox.showinfo("Remove item", "Please select an item to remove.")
            return

        index = int(selected[0])
        self.order_controller.remove_item(index)
        self.refresh_order_view()

    def clear_order(self):
        if not self.order_items:
            return
        if messagebox.askyesno(
            "Clear order", "Are you sure you want to clear the entire order?"
        ):
            self.order_controller.clear()
            self.refresh_order_view()

    def get_current_order_total(self) -> float:
        return self.order_controller.total(
            self.include_service_charge.get(), RESTAURANT["service_charge"]
        )

    def update_session_sales_label(self):
        # Refresh the session orders list for current session.
        try:
            orders = self.session_controller.get_orders(now=datetime.now())
            for row in self.session_orders_listbox.get_children():
                self.session_orders_listbox.delete(row)
            session_total = 0.0
            for idx, order in enumerate(orders):
                ts = order.get("timestamp", "")
                total = float(order.get("total", order.get("amount", 0.0)))
                session_total += total
                order_number = str(order.get("order_number", f"#{idx + 1}"))
                time_display = ts[11:16] if len(ts) >= 16 else "--:--"
                item_names = (
                    ", ".join(
                        f"{item.get('name', '')} x{item.get('qty', item.get('quantity', 1))}"
                        for item in order.get("items", [])
                    )
                    or "Manual sale"
                )
                self.session_orders_listbox.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        order_number,
                        time_display,
                        item_names,
                        format_currency(total),
                    ),
                )
            self.session_summary_label.configure(
                text=f"{len(orders)} tickets  ·  {format_currency(session_total)}"
            )
            if orders:
                last_item = self.session_orders_listbox.get_children()[-1]
                self.session_orders_listbox.selection_set(last_item)
                self.session_orders_listbox.see(last_item)
        except Exception:
            pass

    def display_session_sales(self):
        current_session_sales = get_session_sales(now=datetime.now())
        show_session_sales(self, current_session_sales, format_currency)

    def display_closing_report(self):
        session_id = get_session_id(datetime.now())
        if session_id is None:
            messagebox.showinfo(
                "Closing report",
                "There is no active session. Closing sessions run from 5:00 PM to 3:59 AM.",
                parent=self,
            )
            return

        orders = self.session_controller.get_orders(now=datetime.now())
        report_text = build_closing_report_text(orders, session_id)
        open_closing_report(
            self,
            session_id,
            orders,
            report_text,
            configure_theme(self),
            self.print_with_escpos,
        )

    def display_sales_analytics(self):
        if not getattr(self, "_legacy_report_ui", False):
            return open_sales_analytics(
                self,
                configure_theme(self),
                get_sales_analytics,
                format_currency,
                validate_date_range,
            )

        # Legacy inline implementation retained temporarily for compatibility.
        analytics_window = tk.Toplevel(self)
        analytics_window.title("Sales analytics")
        analytics_window.geometry("760x620")
        analytics_window.minsize(640, 480)
        analytics_window.transient(self)
        colors = configure_theme(self)
        analytics_window.configure(bg=colors["canvas"])
        analytics_window.columnconfigure(0, weight=1)
        analytics_window.rowconfigure(2, weight=1)

        ctk.CTkLabel(
            analytics_window,
            text="Sales analytics",
            text_color=colors["ink"],
            font=("Segoe UI", 21, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 2))
        ctk.CTkLabel(
            analytics_window,
            text="See which menu items sell most and generate the most revenue.",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        filter_frame = ctk.CTkFrame(
            analytics_window, fg_color=colors["panel"], corner_radius=10
        )
        filter_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        filter_frame.columnconfigure(0, weight=1)
        filter_frame.rowconfigure(1, weight=1)
        controls = ctk.CTkFrame(filter_frame, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        start_var = tk.StringVar()
        end_var = tk.StringVar()
        ttk.Label(controls, text="From (YYYY-MM-DD)").pack(side="left", padx=(0, 4))
        ttk.Entry(controls, textvariable=start_var, width=14).pack(
            side="left", padx=(0, 10)
        )
        ttk.Label(controls, text="To (YYYY-MM-DD)").pack(side="left", padx=(0, 4))
        ttk.Entry(controls, textvariable=end_var, width=14).pack(
            side="left", padx=(0, 10)
        )

        tree = ttk.Treeview(
            filter_frame,
            columns=("item", "size", "quantity", "revenue"),
            show="headings",
            style="Modern.Treeview",
        )
        tree.heading("item", text="Item")
        tree.heading("size", text="Size")
        tree.heading("quantity", text="Qty sold")
        tree.heading("revenue", text="Revenue")
        tree.column("item", width=320, anchor="w")
        tree.column("size", width=130, anchor="w")
        tree.column("quantity", width=100, anchor="center")
        tree.column("revenue", width=130, anchor="e")
        tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        scrollbar = ttk.Scrollbar(filter_frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))
        tree.configure(yscrollcommand=scrollbar.set)
        summary_label = ctk.CTkLabel(
            filter_frame,
            text="0 items sold  ·  Revenue: Rs 0.00",
            text_color=colors["brand"],
            font=("Segoe UI", 12, "bold"),
        )
        summary_label.grid(
            row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12)
        )

        def refresh_analytics():
            try:
                start_date, end_date = validate_date_range(
                    start_var.get(), end_var.get()
                )
            except ValueError:
                messagebox.showerror(
                    "Sales analytics",
                    "Enter a valid date range in YYYY-MM-DD format.",
                    parent=analytics_window,
                )
                return

            analytics = get_sales_analytics(start_date=start_date, end_date=end_date)
            for row in tree.get_children():
                tree.delete(row)
            total_quantity = 0
            total_revenue = 0.0
            for item in analytics:
                quantity = int(item["quantity"])
                revenue = float(item["revenue"])
                total_quantity += quantity
                total_revenue += revenue
                tree.insert(
                    "",
                    "end",
                    values=(
                        item["name"],
                        item["size"],
                        quantity,
                        format_currency(revenue),
                    ),
                )
            if not analytics:
                tree.insert("", "end", values=("No item sales recorded", "", "", ""))
            summary_label.configure(
                text=f"{total_quantity} items sold  ·  Revenue: {format_currency(total_revenue)}"
            )

        ctk.CTkButton(
            controls,
            text="Refresh",
            command=refresh_analytics,
            width=90,
            height=32,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
        ).pack(side="left")
        refresh_analytics()

    def display_sales_report(self):
        if not getattr(self, "_legacy_report_ui", False):
            return open_sales_report(
                self,
                configure_theme(self),
                get_sales_report,
                format_currency,
                validate_date_range,
            )

        # Legacy inline implementation retained temporarily for compatibility.
        report_window = tk.Toplevel(self)
        report_window.title("Sales Report")
        report_window.geometry(
            f"{min(900, max(680, report_window.winfo_screenwidth() - 160))}x"
            f"{min(650, max(440, report_window.winfo_screenheight() - 180))}"
        )
        report_window.minsize(620, 420)
        report_window.transient(self)
        colors = configure_theme(self)
        report_window.configure(bg=colors["canvas"])
        report_window.columnconfigure(0, weight=1)
        report_window.rowconfigure(2, weight=1)

        header_frame = ctk.CTkFrame(
            report_window, fg_color=colors["panel"], corner_radius=12
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        ctk.CTkLabel(
            header_frame,
            text="Sales report",
            text_color=colors["ink"],
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(
            header_frame,
            text="Review session totals or filter by a date range.",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=16, pady=(1, 12))

        filter_frame = ctk.CTkFrame(
            report_window, fg_color=colors["panel"], corner_radius=10
        )
        filter_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        ttk.Label(filter_frame, text="From (YYYY-MM-DD)").pack(
            side="left", padx=(12, 4), pady=10
        )
        start_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=start_var, width=14).pack(
            side="left", padx=(0, 8), pady=10
        )
        ttk.Label(filter_frame, text="To (YYYY-MM-DD)").pack(
            side="left", padx=(0, 4), pady=10
        )
        end_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=end_var, width=14).pack(
            side="left", padx=(0, 8), pady=10
        )

        tree = ttk.Treeview(
            report_window,
            columns=("date", "orders", "total"),
            show="headings",
            style="Modern.Treeview",
        )
        tree.heading("date", text="Session date")
        tree.heading("orders", text="Orders")
        tree.heading("total", text="Total sales")
        tree.column("date", width=240, anchor="w")
        tree.column("orders", width=120, anchor="center")
        tree.column("total", width=180, anchor="e")
        tree.grid(row=2, column=0, sticky="nsew", padx=(16, 0), pady=(0, 6))
        report_scrollbar = ttk.Scrollbar(
            report_window, orient="vertical", command=tree.yview
        )
        report_scrollbar.grid(row=2, column=1, sticky="ns", padx=(0, 16), pady=(0, 6))
        tree.configure(yscrollcommand=report_scrollbar.set)
        summary_label = ctk.CTkLabel(
            report_window,
            text="Grand total: Rs 0.00",
            text_color=colors["brand"],
            font=("Segoe UI", 14, "bold"),
            anchor="e",
        )
        summary_label.grid(
            row=3, column=0, columnspan=2, sticky="e", padx=16, pady=(2, 6)
        )

        def refresh_report():
            try:
                start_date, end_date = validate_date_range(
                    start_var.get(), end_var.get()
                )
            except ValueError:
                messagebox.showerror(
                    "Sales report",
                    "Enter a valid date range in YYYY-MM-DD format.",
                    parent=report_window,
                )
                return

            report = get_sales_report(start_date=start_date, end_date=end_date)
            for row in tree.get_children():
                tree.delete(row)
            grand_total = 0.0
            for entry in report:
                grand_total += entry["total"]
                tree.insert(
                    "",
                    "end",
                    values=(
                        entry["session_id"],
                        entry["order_count"],
                        format_currency(entry["total"]),
                    ),
                )
            if not report:
                tree.insert(
                    "", "end", values=("No sales recorded", "", format_currency(0.0))
                )
            summary_label.configure(text=f"Grand total: {format_currency(grand_total)}")

        def export_report():
            start_date = start_var.get().strip() or None
            end_date = end_var.get().strip() or None
            report = get_sales_report(start_date=start_date, end_date=end_date)
            target = filedialog.asksaveasfilename(
                parent=report_window,
                title="Export sales report",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
            )
            if not target:
                return
            with open(target, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Session date", "Orders", "Total sales"])
                writer.writerows(
                    (entry["session_id"], entry["order_count"], entry["total"])
                    for entry in report
                )
            messagebox.showinfo(
                "Sales report",
                "Sales report exported successfully.",
                parent=report_window,
            )

        button_frame = ctk.CTkFrame(report_window, fg_color="transparent")
        button_frame.grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 14)
        )
        export_button = ctk.CTkButton(
            button_frame,
            text="EXPORT CSV",
            command=export_report,
            width=110,
            height=34,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
            font=("Segoe UI", 10, "bold"),
        )
        export_button.pack(side="left")

        filter_button = ctk.CTkButton(
            filter_frame,
            text="FILTER",
            command=refresh_report,
            width=90,
            height=32,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 10, "bold"),
        )
        filter_button.pack(side="left", padx=(4, 12), pady=10)

        refresh_report()

    def show_session_order_context_menu(self, event):
        if not self.session_orders_listbox.get_children():
            return

        row = self.session_orders_listbox.identify_row(event.y)
        if not row:
            return

        self.session_orders_listbox.selection_set(row)
        self.show_selected_order_details()
        self.session_order_context_menu.tk_popup(event.x_root, event.y_root)

    def load_session_order_into_current_order(
        self, order: dict, order_index: int | None = None
    ) -> None:
        self.order_controller.replace(deserialize_order_items(order.get("items", [])))

        self.editing_session_order_index = order_index
        self.refresh_order_view()

    def edit_selected_session_order(self):
        selection = self.session_orders_listbox.selection()
        if not selection:
            return

        order_index = int(selection[0])
        orders = self.session_controller.get_orders(now=datetime.now())
        if order_index < 0 or order_index >= len(orders):
            return

        order = orders[order_index]
        self.load_session_order_into_current_order(order, order_index)

    def delete_selected_session_order(self):
        selection = self.session_orders_listbox.selection()
        if not selection:
            return

        order_index = int(selection[0])
        orders = self.session_controller.get_orders(now=datetime.now())
        if order_index < 0 or order_index >= len(orders):
            return

        order = orders[order_index]
        if not messagebox.askyesno(
            "Delete Order", f"Delete this order from {order.get('timestamp', '')}?"
        ):
            return

        self.session_controller.delete_order(order_index, now=datetime.now())
        self.refresh_session_orders_view()

    def show_selected_order_details(self):
        try:
            sel = self.session_orders_listbox.selection()
            if not sel:
                return
            index = int(sel[0])
            orders = get_session_orders(now=datetime.now())
            if index < 0 or index >= len(orders):
                return
            order = orders[index]
            order_total = float(order.get("total", order.get("amount", 0.0)))
            timestamp = order.get("timestamp", "")[:19].replace("T", " ")
            destination = f"{order.get('table_type', 'Indoor')} {order.get('table_number', '')}".rstrip()
            self.order_detail_header.configure(
                text=f"{order.get('order_number', f'Order {index + 1}')}  ·  {format_currency(order_total)}"
            )
            self.order_detail_meta.configure(text=f"{timestamp}  ·  {destination}")
            for row in self.order_detail_tree.get_children():
                self.order_detail_tree.delete(row)
            for item in order.get("items", []):
                name = item.get("name", "")
                qty = item.get("qty", item.get("quantity", 1))
                size = item.get("size", "")
                total = item.get(
                    "total", item.get("total_price", item.get("amount", 0.0))
                )
                self.order_detail_tree.insert(
                    "", "end", values=(name, size, qty, format_currency(float(total)))
                )
        except Exception:
            pass

    def refresh_session_orders_view(self):
        self.update_session_sales_label()
        if not self.session_orders_listbox.get_children():
            self.order_detail_header.configure(text="No orders yet")
            self.order_detail_meta.configure(text="Completed tickets will appear here.")
            for row in self.order_detail_tree.get_children():
                self.order_detail_tree.delete(row)
            return
        self.show_selected_order_details()

    def refresh_order_view(self):
        for row in self.order_tree.get_children():
            self.order_tree.delete(row)

        for idx, item in enumerate(self.order_items):
            self.order_tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    item["name"],
                    item["size"],
                    format_currency(item["unit_price"]),
                    item["quantity"],
                    format_currency(item["total_price"]),
                ),
            )

        total_amount = self.get_current_order_total()
        self.total_label.configure(text=f"Total: {format_currency(total_amount)}")
        self.update_session_sales_label()

    def get_windows_printers(self) -> list[str]:
        return service_get_windows_printers()

    def get_default_printer(self) -> str | None:
        return service_get_default_printer()

    def open_printer_settings(self):
        settings_window = tk.Toplevel(self)
        settings_window.title("Printer settings")
        settings_window.geometry("520x220")
        settings_window.resizable(False, False)
        settings_window.transient(self)
        settings_window.grab_set()

        colors = configure_theme(self)
        settings_window.configure(bg=colors["canvas"])
        ctk.CTkLabel(
            settings_window,
            text="Printer settings",
            text_color=colors["ink"],
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w", padx=22, pady=(20, 2))
        ctk.CTkLabel(
            settings_window,
            text="Choose the Windows printer used for receipts and kitchen slips.",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=22, pady=(0, 14))

        printer_var = tk.StringVar(value=RESTAURANT.get("printer_name", ""))
        printer_row = ctk.CTkFrame(settings_window, fg_color="transparent")
        printer_row.pack(fill="x", padx=22)
        printer_row.columnconfigure(0, weight=1)
        printer_menu = ttk.Combobox(
            printer_row,
            textvariable=printer_var,
            values=self.get_windows_printers(),
            state="normal",
        )
        printer_menu.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            printer_row,
            text="Refresh",
            command=lambda: printer_menu.configure(values=self.get_windows_printers()),
            width=86,
            height=36,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).grid(row=0, column=1)

        def save_printer_setting():
            restaurant = RESTAURANT.copy()
            restaurant["printer_name"] = printer_var.get().strip()
            save_restaurant(restaurant)
            settings_window.destroy()

        ctk.CTkButton(
            settings_window,
            text="Save printer",
            command=save_printer_setting,
            height=38,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 11, "bold"),
        ).pack(fill="x", padx=22, pady=18)

    def open_backup_restore(self):
        backup_window = tk.Toplevel(self)
        backup_window.title("Backup and restore")
        backup_window.geometry("560x430")
        backup_window.minsize(500, 360)
        backup_window.transient(self)
        backup_window.grab_set()
        colors = configure_theme(self)
        backup_window.configure(bg=colors["canvas"])

        ctk.CTkLabel(
            backup_window,
            text="Backup and restore",
            text_color=colors["ink"],
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 2))
        ctk.CTkLabel(
            backup_window,
            text="Backups include settings, menu, sales, and staff access data.",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        list_frame = ctk.CTkFrame(
            backup_window, fg_color=colors["panel"], corner_radius=10
        )
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        backup_list = tk.Listbox(
            list_frame,
            activestyle="none",
            font=("Segoe UI", 11),
            bg=colors["panel"],
            fg=colors["ink"],
            relief="flat",
        )
        backup_list.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)
        backup_scroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=backup_list.yview
        )
        backup_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        backup_list.configure(yscrollcommand=backup_scroll.set)

        backups = list_backups()
        for backup in backups:
            backup_list.insert("end", backup.name)

        def refresh_backups():
            backup_list.delete(0, "end")
            for backup in list_backups():
                backup_list.insert("end", backup.name)

        def make_backup():
            try:
                backup = create_backup()
                refresh_backups()
                messagebox.showinfo(
                    "Backup and restore",
                    f"Backup created: {backup.name}",
                    parent=backup_window,
                )
            except OSError as exc:
                messagebox.showerror(
                    "Backup and restore", str(exc), parent=backup_window
                )

        def export_backup():
            selection = backup_list.curselection()
            if not selection:
                messagebox.showinfo(
                    "Backup and restore", "Select a backup first.", parent=backup_window
                )
                return
            source = list_backups()[selection[0]]
            target = filedialog.asksaveasfilename(
                parent=backup_window,
                title="Export backup archive",
                defaultextension=".zip",
                filetypes=[("ZIP archives", "*.zip")],
            )
            if target:
                shutil.make_archive(str(Path(target).with_suffix("")), "zip", source)
                messagebox.showinfo(
                    "Backup and restore", "Backup exported.", parent=backup_window
                )

        def restore_selected_backup():
            selection = backup_list.curselection()
            if not selection:
                messagebox.showinfo(
                    "Backup and restore", "Select a backup first.", parent=backup_window
                )
                return
            source = list_backups()[selection[0]]
            if not messagebox.askyesno(
                "Restore backup",
                "Restore this backup? The current data will be replaced and the app will restart.",
                parent=backup_window,
            ):
                return
            try:
                restore_backup(source)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Restore backup", str(exc), parent=backup_window)
                return
            messagebox.showinfo(
                "Restore backup",
                "Backup restored. The application will now restart.",
                parent=backup_window,
            )
            self.destroy()
            os.execl(sys.executable, sys.executable, *sys.argv)

        action_frame = ctk.CTkFrame(backup_window, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=(0, 18))
        ctk.CTkButton(
            action_frame, text="Create backup", command=make_backup, height=38
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(
            action_frame,
            text="Export selected",
            command=export_backup,
            height=38,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(
            action_frame,
            text="Restore selected",
            command=restore_selected_backup,
            height=38,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

    def print_with_windows_spooler(self, text: str, printer_name: str) -> None:
        service_print_with_windows_spooler(text, printer_name)

    def print_with_escpos(self, text: str, printer_name: str | None = None) -> tuple:
        return service_print_with_escpos(text, RESTAURANT, printer_name)

    def print_slip(self):
        if not self.order_items:
            messagebox.showinfo("Print slip", "No items in the order to print.")
            return

        order_total = self.get_current_order_total()
        order_entry = {
            "total": order_total,
            "table_type": self.table_type.get(),
            "table_number": self.table_number.get(),
            "include_service_charge": self.include_service_charge.get(),
            "items": serialize_order_items(self.order_items),
        }
        replace_index = self.editing_session_order_index
        order_number = get_next_order_number(
            now=datetime.now(), replace_index=replace_index
        )
        order_entry["order_number"] = order_number
        record_session_order(
            order_entry, now=datetime.now(), replace_index=replace_index
        )
        self.editing_session_order_index = None
        self.update_session_sales_label()

        receipt_text = build_receipt_text(
            self.order_items,
            self.table_type.get(),
            self.table_number.get(),
            include_service_charge=self.include_service_charge.get(),
            order_number=order_number,
        )
        kitchen_text = build_kitchen_slip_text(
            self.order_items,
            self.table_type.get(),
            self.table_number.get(),
            order_number=order_number,
        )
        print(receipt_text)
        print(kitchen_text)

        # Show both receipt and kitchen windows immediately
        self.show_receipt_window(receipt_text)
        self.show_kitchen_window(kitchen_text)

        # Run printing in a separate thread to avoid freezing UI
        print_thread = threading.Thread(
            target=self.do_print_slip, args=(receipt_text, kitchen_text), daemon=True
        )
        print_thread.start()

    def do_print_slip(self, receipt_text: str, kitchen_text: str):
        """Background thread worker for printing receipts."""
        try:
            if os.name == "nt":
                receipt_success, receipt_message, _ = self.print_with_escpos(
                    receipt_text
                )
                kitchen_success, kitchen_message, _ = self.print_with_escpos(
                    kitchen_text
                )

                if receipt_success and kitchen_success:
                    printer_message = "Receipts sent to printer successfully"
                else:
                    printer_message = (
                        f"Receipt: {receipt_message}\nKitchen: {kitchen_message}"
                    )
            else:
                printer_message = "Automatic printing is only supported on Windows."

            # Show completion message in UI thread
            self.after(0, lambda: messagebox.showinfo("Print Status", printer_message))

        except Exception as exc:
            error_message = f"Unable to print receipt: {exc}"
            self.after(0, lambda: messagebox.showerror("Print slip", error_message))

    def show_receipt_window(self, receipt_text: str):
        receipt_window = tk.Toplevel(self)
        receipt_window.title("Receipt")
        receipt_window.geometry(
            f"{min(560, max(380, receipt_window.winfo_screenwidth() // 3))}x"
            f"{min(800, max(560, receipt_window.winfo_screenheight() - 160))}"
        )

        logo_path = RESTAURANT["logo_path"]
        logo_image = load_preview_image(logo_path, (320, 120), receipt_window)
        if logo_image:
            logo_label = ttk.Label(receipt_window, image=logo_image)
            logo_label.image = logo_image
            logo_label.pack(pady=8)

        text_area = tk.Text(
            receipt_window, wrap="none", padx=0, pady=0, font=("Courier New", 6)
        )
        text_area.insert("0.0", receipt_text)
        text_area.config(state="disabled")
        text_area.pack(fill="both", expand=True)

        footer_path = RESTAURANT["footer_path"]
        footer_image = load_preview_image(footer_path, (320, 80), receipt_window)
        if footer_image:
            footer_label = ttk.Label(receipt_window, image=footer_image)
            footer_label.image = footer_image
            footer_label.pack(pady=8)

        ttk.Button(receipt_window, text="Close", command=receipt_window.destroy).pack(
            pady=10
        )

    def show_kitchen_window(self, kitchen_text: str):
        """Display the kitchen slip in a separate window."""
        kitchen_window = tk.Toplevel(self)
        kitchen_window.title("Kitchen Slip")
        kitchen_window.geometry(
            f"{min(560, max(380, kitchen_window.winfo_screenwidth() // 3))}x"
            f"{min(720, max(500, kitchen_window.winfo_screenheight() - 220))}"
        )

        # Add a header to indicate this is for kitchen staff
        header_label = ttk.Label(
            kitchen_window, text="KITCHEN SLIP", font=("Courier New", 10, "bold")
        )
        header_label.pack(pady=10)

        text_area = tk.Text(
            kitchen_window, wrap="none", padx=10, pady=10, font=("Courier New", 8)
        )
        text_area.insert("0.0", kitchen_text)

        text_area.config(state="disabled")
        text_area.pack(fill="both", expand=True)

        ttk.Button(kitchen_window, text="Close", command=kitchen_window.destroy).pack(
            pady=10
        )


def main():
    LOGGER.info("Starting Restaurant POS")
    try:
        app = RestaurantPOS()
        app.mainloop()
    except Exception:
        LOGGER.exception("Restaurant POS terminated unexpectedly")
        raise


if __name__ == "__main__":
    main()
