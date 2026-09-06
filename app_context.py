from dataclasses import dataclass
from pathlib import Path

@dataclass
class AppContext:
    data_dir: Path
    restaurant_path: Path
    menu_items_path: Path
    session_sales_path: Path
    pin_path: Path
    backup_dir: Path
    restaurant: dict
    menu_items: list[dict]
