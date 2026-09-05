import csv
import hashlib
import hmac
import json
import os
import re
import tempfile
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import customtkinter as ctk

from domain.pricing import calculate_order_total
from domain.pricing import get_categories as get_menu_categories
from domain.pricing import \
    get_items_for_category as get_menu_items_for_category
from domain.pricing import get_price_for_item as get_menu_price
from domain.pricing import get_sizes_for_item as get_menu_sizes_for_item
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
from services.receipt_service import \
    build_kitchen_slip_text as service_build_kitchen_slip_text
from services.receipt_service import \
    build_receipt_text as service_build_receipt_text
from services.receipt_service import format_currency as service_format_currency
from ui.theme import configure_theme

try:
    from escpos.printer import Win32Raw

    ESC_POS_AVAILABLE = True
except Exception:
    Win32Raw = None
    ESC_POS_AVAILABLE = False

try:
    import win32print

    WIN32_PRINT_AVAILABLE = True
except ImportError:
    win32print = None
    WIN32_PRINT_AVAILABLE = False

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

RESTAURANT = repository_load_restaurant(RESTAURANT_PATH)
MENU_ITEMS = repository_load_menu_items([], MENU_ITEMS_PATH, include_defaults=False)


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
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def verify_pin(pin: str, pin_path: str | os.PathLike = PIN_PATH) -> bool:
    try:
        stored_hash = Path(pin_path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return False
    return hmac.compare_digest(hash_pin(pin), stored_hash)


def save_pin(pin: str, pin_path: str | os.PathLike = PIN_PATH) -> None:
    target_path = Path(pin_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(hash_pin(pin), encoding="utf-8")


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
        self.apply_window_icon()
        self.resizable(True, True)
        try:
            self.state("zoomed")
        except Exception:
            pass

        self.order_items = []
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
            if not phone or not re.fullmatch(r"[+()\d][\d\s().-]{6,19}", phone):
                messagebox.showerror(
                    "Restaurant setup",
                    "Enter a valid phone number.",
                    parent=setup_window,
                )
                return
            if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                messagebox.showerror(
                    "Restaurant setup",
                    "Enter a valid email address.",
                    parent=setup_window,
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
                if image_path and (
                    not Path(image_path).is_file()
                    or Path(image_path).suffix.lower() not in extensions
                ):
                    messagebox.showerror(
                        "Restaurant setup",
                        f"Choose a valid {label.lower()} file.",
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
        setup_window.bind("<Return>", lambda event: submit())

    def authenticate_user(self) -> bool:
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()
        if PIN_PATH.exists():
            pin = simpledialog.askstring(
                "Staff login", "Enter PIN:", parent=self, show="*"
            )
            if not pin or not verify_pin(pin):
                messagebox.showerror("Staff login", "Incorrect PIN.")
                return False
        else:
            pin = simpledialog.askstring(
                "Create PIN", "Create a PIN for this app:", parent=self, show="*"
            )
            confirmation = simpledialog.askstring(
                "Create PIN", "Confirm your PIN:", parent=self, show="*"
            )
            if (
                not pin
                or not pin.isdigit()
                or pin != confirmation
                or not 4 <= len(pin) <= 12
            ):
                messagebox.showerror(
                    "Create PIN", "PINs must match and contain 4-12 digits."
                )
                return False
            save_pin(pin)
        return True

    def change_pin(self):
        current_pin = simpledialog.askstring(
            "Change PIN", "Enter current PIN:", parent=self, show="*"
        )
        if not current_pin or not verify_pin(current_pin):
            messagebox.showerror("Change PIN", "Current PIN is incorrect.", parent=self)
            return

        new_pin = simpledialog.askstring(
            "Change PIN", "Enter new PIN (4-12 digits):", parent=self, show="*"
        )
        confirmation = simpledialog.askstring(
            "Change PIN", "Confirm new PIN:", parent=self, show="*"
        )
        if (
            not new_pin
            or not new_pin.isdigit()
            or not 4 <= len(new_pin) <= 12
            or new_pin != confirmation
        ):
            messagebox.showerror(
                "Change PIN", "PINs must match and contain 4-12 digits.", parent=self
            )
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

        item_frame = ctk.CTkFrame(self, fg_color=colors["panel"], corner_radius=14)
        item_frame.grid(row=1, column=0, sticky="nsew", padx=(18, 8), pady=(8, 10))
        item_frame.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            item_frame,
            text="Build an order",
            text_color=colors["ink"],
            font=("Segoe UI", 20, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 2))
        ctk.CTkLabel(
            item_frame,
            text="Choose a category, item, size, and quantity.",
            text_color=colors["muted"],
            font=("Segoe UI", 11),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 16))
        form_frame = ctk.CTkFrame(item_frame, fg_color=colors["soft"], corner_radius=10)
        form_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=2)
        form_frame.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            form_frame,
            text="CATEGORY",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        self.category_menu = ttk.Combobox(
            form_frame,
            textvariable=self.selected_category,
            values=self.categories,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.category_menu.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(
            form_frame,
            text="MENU ITEM",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(4, 4))
        self.item_menu = ttk.Combobox(
            form_frame,
            textvariable=self.selected_item,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.item_menu.grid(row=3, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.category_menu.bind("<<ComboboxSelected>>", self.update_items)
        ctk.CTkLabel(
            form_frame,
            text="SIZE",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=4, column=0, sticky="w", padx=12, pady=(4, 4))
        self.size_menu = ttk.Combobox(
            form_frame,
            textvariable=self.selected_size,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.size_menu.grid(row=5, column=0, padx=12, pady=(0, 10), sticky="ew")
        self.item_menu.bind("<<ComboboxSelected>>", self.update_sizes)

        self.price_label = ctk.CTkLabel(
            form_frame,
            text="Unit price: Rs 0.00",
            text_color=colors["brand"],
            font=("Segoe UI", 13, "bold"),
        )
        self.price_label.grid(row=6, column=0, pady=(2, 12))
        self.update_items()
        self.size_menu.bind("<<ComboboxSelected>>", lambda event: self.update_price())
        quantity_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
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
            command=lambda: self.change_quantity(-1),
            width=38,
            height=38,
            corner_radius=7,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        ctk.CTkEntry(
            quantity_stepper,
            textvariable=self.quantity,
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
            command=lambda: self.change_quantity(1),
            width=38,
            height=38,
            corner_radius=7,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        ctk.CTkButton(
            item_frame,
            text="+  ADD TO ORDER",
            command=self.add_item_to_order,
            height=46,
            corner_radius=9,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 12, "bold"),
        ).grid(row=4, column=0, sticky="ew", padx=18, pady=(4, 18))

        middle_container = ctk.CTkFrame(self, fg_color="transparent")
        middle_container.grid(
            row=1, column=1, rowspan=2, sticky="nsew", padx=(10, 4), pady=(8, 18)
        )
        middle_container.columnconfigure(0, weight=1)
        middle_container.rowconfigure(1, weight=1)

        table_frame = ctk.CTkFrame(
            item_frame, fg_color=colors["panel"], corner_radius=14
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
            textvariable=self.table_type,
            values=["Indoor", "Outdoor", "Home Delivery"],
            state="readonly",
            style="Modern.TCombobox",
        )
        self.table_type_menu.grid(row=1, column=1, padx=(0, 16), pady=3, sticky="ew")
        self.table_type_menu.bind("<<ComboboxSelected>>", self.update_table_numbers)
        ctk.CTkLabel(
            table_frame,
            text="TABLE",
            text_color=colors["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=16, pady=3)
        self.table_number_menu = ttk.Combobox(
            table_frame,
            textvariable=self.table_number,
            state="readonly",
            style="Modern.TCombobox",
        )
        self.table_number_menu.grid(row=2, column=1, padx=(0, 16), pady=3, sticky="ew")
        self.service_charge_check = ctk.CTkCheckBox(
            table_frame,
            text="Add Service Charge",
            variable=self.include_service_charge,
            command=self.refresh_order_view,
            text_color=colors["muted"],
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
        )
        self.service_charge_check.grid(
            row=3, column=0, columnspan=2, sticky="w", padx=16, pady=(4, 8)
        )
        self.update_table_numbers()

        summary_frame = ctk.CTkFrame(
            middle_container, fg_color=colors["brand"], corner_radius=14
        )
        summary_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ctk.CTkLabel(
            summary_frame,
            text="CURRENT TOTAL",
            text_color="#F4DCE0",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=20, pady=(20, 2))
        self.total_label = ctk.CTkLabel(
            summary_frame,
            text="Total: Rs 0.00",
            text_color="white",
            font=("Segoe UI", 28, "bold"),
        )
        self.total_label.pack(anchor="w", padx=20, pady=(0, 18))
        ctk.CTkButton(
            summary_frame,
            text="View session sales",
            command=self.display_session_sales,
            height=38,
            fg_color="#A94353",
            hover_color=colors["brand_dark"],
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            summary_frame,
            text="Sales report",
            command=self.display_sales_report,
            height=38,
            fg_color="#A94353",
            hover_color=colors["brand_dark"],
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            summary_frame,
            text="Change PIN",
            command=self.change_pin,
            height=38,
            fg_color="#A94353",
            hover_color=colors["brand_dark"],
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(
            middle_container,
            text="Manage menu",
            command=self.open_menu_manager,
            height=38,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            text_color="white",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=3, column=0, sticky="ew", pady=(10, 0))

        orders_panel = ctk.CTkFrame(self, fg_color=colors["panel"], corner_radius=14)
        orders_panel.grid(
            row=1, column=2, rowspan=2, sticky="nsew", padx=(4, 18), pady=(8, 18)
        )

        ctk.CTkLabel(
            orders_panel,
            text="Session orders",
            text_color=colors["ink"],
            font=("Segoe UI", 19, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 2))
        self.session_summary_label = ctk.CTkLabel(
            orders_panel,
            text="0 tickets  ·  Rs 0.00",
            text_color=colors["brand"],
            font=("Segoe UI", 11, "bold"),
        )
        self.session_summary_label.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 10)
        )
        orders_panel.columnconfigure(0, weight=1)
        orders_panel.rowconfigure(2, weight=3)
        orders_panel.rowconfigure(3, weight=2)
        self.session_orders_listbox = ttk.Treeview(
            orders_panel,
            columns=("order", "time", "items", "total"),
            show="headings",
            selectmode="browse",
            style="Modern.Treeview",
        )
        self.session_orders_listbox.heading("order", text="Order")
        self.session_orders_listbox.heading("time", text="Time")
        self.session_orders_listbox.heading("items", text="Items")
        self.session_orders_listbox.heading("total", text="Total")
        self.session_orders_listbox.column("order", width=92, anchor="w", stretch=False)
        self.session_orders_listbox.column(
            "time", width=70, anchor="center", stretch=False
        )
        self.session_orders_listbox.column("items", width=130, anchor="w")
        self.session_orders_listbox.column("total", width=92, anchor="e", stretch=False)
        self.session_orders_listbox.grid(
            row=2, column=0, sticky="nsew", padx=(12, 0), pady=6
        )
        orders_scrollbar = ttk.Scrollbar(
            orders_panel, orient="vertical", command=self.session_orders_listbox.yview
        )
        orders_scrollbar.grid(row=2, column=1, sticky="ns", padx=(0, 10), pady=6)
        detail_frame = ctk.CTkFrame(
            orders_panel, fg_color=colors["soft"], corner_radius=8
        )
        detail_frame.grid(
            row=3, column=0, columnspan=2, sticky="nsew", padx=12, pady=(4, 12)
        )
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(2, weight=1)
        self.order_detail_header = ctk.CTkLabel(
            detail_frame,
            text="Select an order",
            text_color=colors["ink"],
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        )
        self.order_detail_header.grid(
            row=0, column=0, sticky="ew", padx=12, pady=(10, 0)
        )
        self.order_detail_meta = ctk.CTkLabel(
            detail_frame,
            text="",
            text_color=colors["muted"],
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.order_detail_meta.grid(row=1, column=0, sticky="ew", padx=12, pady=(1, 5))
        self.order_detail_tree = ttk.Treeview(
            detail_frame,
            columns=("item", "size", "qty", "total"),
            show="headings",
            height=3,
            style="Modern.Treeview",
        )
        self.order_detail_tree.heading("item", text="Item")
        self.order_detail_tree.heading("size", text="Size")
        self.order_detail_tree.heading("qty", text="Qty")
        self.order_detail_tree.heading("total", text="Total")
        self.order_detail_tree.column("item", anchor="w", width=150)
        self.order_detail_tree.column("size", anchor="center", width=68, stretch=False)
        self.order_detail_tree.column("qty", anchor="center", width=45, stretch=False)
        self.order_detail_tree.column("total", anchor="e", width=78, stretch=False)
        self.order_detail_tree.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        detail_scrollbar = ttk.Scrollbar(
            detail_frame, orient="vertical", command=self.order_detail_tree.yview
        )
        detail_scrollbar.grid(row=2, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
        self.order_detail_tree.configure(yscrollcommand=detail_scrollbar.set)
        self.session_orders_listbox.configure(yscrollcommand=orders_scrollbar.set)
        self.session_orders_listbox.bind(
            "<<TreeviewSelect>>", lambda e: self.show_selected_order_details()
        )
        self.session_orders_listbox.bind(
            "<Button-3>", self.show_session_order_context_menu
        )

        self.session_order_context_menu = tk.Menu(self, tearoff=0)
        self.session_order_context_menu.add_command(
            label="Edit Order", command=self.edit_selected_session_order
        )
        self.session_order_context_menu.add_command(
            label="Delete Order", command=self.delete_selected_session_order
        )

        order_frame = ctk.CTkFrame(
            middle_container, fg_color=colors["panel"], corner_radius=14
        )
        order_frame.grid(row=1, column=0, sticky="nsew")
        order_frame.columnconfigure(0, weight=1)
        order_frame.rowconfigure(0, weight=0)
        order_frame.rowconfigure(1, weight=1)
        ctk.CTkLabel(
            order_frame,
            text="Current order",
            text_color=colors["ink"],
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="nw", padx=16, pady=(14, 0))
        self.order_tree = ttk.Treeview(
            order_frame,
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
            order_frame, orient="vertical", command=self.order_tree.yview
        )
        self.order_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(4, 6))
        action_frame = ctk.CTkFrame(order_frame, fg_color="transparent")
        action_frame.grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12)
        )
        action_frame.columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(
            action_frame,
            text="Remove selected",
            command=self.remove_selected_item,
            height=36,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(
            action_frame,
            text="Clear order",
            command=self.clear_order,
            height=36,
            fg_color=colors["soft"],
            hover_color=colors["line"],
            text_color=colors["ink"],
        ).grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkButton(
            action_frame,
            text="PRINT RECEIPT  ->",
            command=self.print_slip,
            height=36,
            fg_color=colors["brand"],
            hover_color=colors["brand_dark"],
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=2, sticky="ew", padx=(5, 0))

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
        total = price * qty

        self.order_items.append(
            {
                "name": item_name,
                "size": size,
                "quantity": qty,
                "unit_price": price,
                "total_price": total,
            }
        )
        self.refresh_order_view()

    def remove_selected_item(self):
        selected = self.order_tree.selection()
        if not selected:
            messagebox.showinfo("Remove item", "Please select an item to remove.")
            return

        index = int(selected[0])
        self.order_items.pop(index)
        self.refresh_order_view()

    def clear_order(self):
        if not self.order_items:
            return
        if messagebox.askyesno(
            "Clear order", "Are you sure you want to clear the entire order?"
        ):
            self.order_items.clear()
            self.refresh_order_view()

    def get_current_order_total(self) -> float:
        return calculate_order_total(
            self.order_items,
            include_service_charge=self.include_service_charge.get(),
            service_charge=RESTAURANT["service_charge"],
        )

    def update_session_sales_label(self):
        # Refresh the session orders list for current session.
        try:
            orders = get_session_orders(now=datetime.now())
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
        messagebox.showinfo(
            "Session Sales", f"Session Sales: {format_currency(current_session_sales)}"
        )

    def display_sales_report(self):
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
            start_date = start_var.get().strip() or None
            end_date = end_var.get().strip() or None
            try:
                for value in (start_date, end_date):
                    if value:
                        datetime.strptime(value, "%Y-%m-%d")
                if start_date and end_date and start_date > end_date:
                    raise ValueError
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
        self.order_items = []
        for item in order.get("items", []) or []:
            quantity = item.get("quantity", item.get("qty", 1))
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                quantity = 1

            unit_price = item.get("unit_price", item.get("price", 0.0))
            total_price = item.get(
                "total_price",
                item.get("total", item.get("amount", float(unit_price) * quantity)),
            )

            self.order_items.append(
                {
                    "name": item.get("name", ""),
                    "size": item.get("size", ""),
                    "quantity": quantity,
                    "unit_price": float(unit_price),
                    "total_price": float(total_price),
                }
            )

        self.editing_session_order_index = order_index
        self.refresh_order_view()

    def edit_selected_session_order(self):
        selection = self.session_orders_listbox.selection()
        if not selection:
            return

        order_index = int(selection[0])
        orders = get_session_orders(now=datetime.now())
        if order_index < 0 or order_index >= len(orders):
            return

        order = orders[order_index]
        self.load_session_order_into_current_order(order, order_index)

    def delete_selected_session_order(self):
        selection = self.session_orders_listbox.selection()
        if not selection:
            return

        order_index = int(selection[0])
        orders = get_session_orders(now=datetime.now())
        if order_index < 0 or order_index >= len(orders):
            return

        order = orders[order_index]
        if not messagebox.askyesno(
            "Delete Order", f"Delete this order from {order.get('timestamp', '')}?"
        ):
            return

        delete_session_order(order_index, now=datetime.now())
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

    def print_to_file(self, text: str) -> str:
        """Save receipt to a file when printer is unavailable."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(os.path.dirname(__file__), "Output")
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, f"receipt_{timestamp}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        return file_path

    def get_windows_printers(self) -> list[str]:
        if not WIN32_PRINT_AVAILABLE or win32print is None:
            return []
        try:
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            return [entry[2] for entry in win32print.EnumPrinters(flags)]
        except Exception:
            return []

    def get_default_printer(self) -> str | None:
        if not WIN32_PRINT_AVAILABLE or win32print is None:
            return None
        try:
            return win32print.GetDefaultPrinter()
        except Exception:
            printers = self.get_windows_printers()
            return printers[0] if printers else None

    def print_with_windows_spooler(self, text: str, printer_name: str) -> None:
        if not WIN32_PRINT_AVAILABLE or win32print is None:
            raise RuntimeError("Windows printing is not available")
        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(
                handle, 1, ("Restaurant POS receipt", None, "RAW")
            )
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, text.encode("cp437", errors="replace"))
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)

    def print_with_escpos(self, text: str, printer_name: str | None = None) -> tuple:
        """
        Print to ESC/POS printer. If printer is unavailable, save to file instead.
        Returns: (success: bool, message: str, file_path: str or None)
        """
        printer_name = printer_name or self.get_default_printer()
        if not printer_name:
            file_path = self.print_to_file(text)
            return (False, f"No Windows printer found, saved to file: {file_path}", file_path)

        if ESC_POS_AVAILABLE and Win32Raw is not None:
            try:
                printer = None
                try:
                    printer = Win32Raw(printer_name)
                    printer.set(align="center", bold=True)
                    printer.textln(RESTAURANT["name"])

                    printer.set(align="center", bold=False, width=1, height=1)
                    printer.textln(RESTAURANT["address"])
                    if RESTAURANT["phone"]:
                        printer.textln(f'Phone: {RESTAURANT["phone"]}')
                    if RESTAURANT["email"]:
                        printer.textln(RESTAURANT["email"])
                    printer.textln("-" * 48)
                    printer.set(align="left")
                    for line in text.splitlines():
                        printer.textln(line)

                    printer.cut()
                    return (True, "sent to printer", None)
                finally:
                    if printer:
                        try:
                            printer.close()
                        except:
                            pass
            except Exception as printer_error:
                print(f"ESC/POS unavailable on {printer_name}: {printer_error}")

        try:
            self.print_with_windows_spooler(text, printer_name)
            return (True, f"sent to printer: {printer_name}", None)
        except Exception as printer_error:
            print(f"Windows printer unavailable: {printer_error}")
            file_path = self.print_to_file(text)
            return (
                False,
                f"Printer unavailable, saved to file: {file_path}",
                file_path,
            )

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
            "items": [
                {
                    "name": it["name"],
                    "size": it["size"],
                    "qty": it["quantity"],
                    "unit_price": it["unit_price"],
                    "total": it["total_price"],
                }
                for it in self.order_items
            ],
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
            receipt_temp = tempfile.NamedTemporaryFile(
                "w", delete=False, suffix=".txt", encoding="utf-8"
            )
            receipt_temp.write(receipt_text)
            receipt_temp.close()

            kitchen_temp = tempfile.NamedTemporaryFile(
                "w", delete=False, suffix="_kitchen.txt", encoding="utf-8"
            )
            kitchen_temp.write(kitchen_text)
            kitchen_temp.close()

            temp_receipt_filename = receipt_temp.name
            temp_kitchen_filename = kitchen_temp.name

            if os.name == "nt":
                # Try to print with ESC/POS (will fall back to file if printer unavailable)
                receipt_success, receipt_message, receipt_file = self.print_with_escpos(
                    receipt_text
                )
                kitchen_success, kitchen_message, kitchen_file = self.print_with_escpos(
                    kitchen_text
                )

                if receipt_success and kitchen_success:
                    printer_message = "Receipts sent to printer successfully"
                elif receipt_file and kitchen_file:
                    printer_message = f"Printer unavailable - saved to:\n  Receipt: {receipt_file}\n  Kitchen: {kitchen_file}"
                else:
                    printer_message = (
                        f"Receipt: {receipt_message}\nKitchen: {kitchen_message}"
                    )
            else:
                printer_message = (
                    f"Saved to {temp_receipt_filename} and {temp_kitchen_filename}"
                )

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
        if PIL_AVAILABLE and logo_path and os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img.thumbnail(
                    (320, 120),
                    (
                        Image.Resampling.LANCZOS
                        if hasattr(Image, "Resampling")
                        else Image.ANTIALIAS
                    ),
                )
                logo_image = ImageTk.PhotoImage(img)
                logo_label = ttk.Label(receipt_window, image=logo_image)
                logo_label.image = logo_image
                logo_label.pack(pady=8)
            except Exception:
                pass

        text_area = tk.Text(
            receipt_window, wrap="none", padx=0, pady=0, font=("Courier New", 6)
        )
        text_area.insert("0.0", receipt_text)
        text_area.config(state="disabled")
        text_area.pack(fill="both", expand=True)

        footer_path = RESTAURANT["footer_path"]
        if PIL_AVAILABLE and footer_path and os.path.exists(footer_path):
            try:
                img = Image.open(footer_path)
                img.thumbnail(
                    (320, 80),
                    (
                        Image.Resampling.LANCZOS
                        if hasattr(Image, "Resampling")
                        else Image.ANTIALIAS
                    ),
                )
                footer_image = ImageTk.PhotoImage(img)
                footer_label = ttk.Label(receipt_window, image=footer_image)
                footer_label.image = footer_image
                footer_label.pack(pady=8)
            except Exception:
                pass

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
    app = RestaurantPOS()
    app.mainloop()


if __name__ == "__main__":
    main()
