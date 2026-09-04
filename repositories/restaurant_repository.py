import json
import os
from pathlib import Path


DEFAULT_RESTAURANT = {
    "name": "",
    "address": "",
    "phone": "",
    "email": "",
    "logo_path": "",
    "app_icon_path": "",
    "footer_path": "",
    "service_charge": 0.0,
    "indoor_tables": 10,
    "outdoor_tables": 25,
}


def load_restaurant(storage_path: str | os.PathLike) -> dict:
    target_path = Path(storage_path)
    if not target_path.exists():
        return DEFAULT_RESTAURANT.copy()
    try:
        with target_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            restaurant = DEFAULT_RESTAURANT.copy()
            restaurant.update(data)
            restaurant["service_charge"] = float(restaurant.get("service_charge", 0.0))
            restaurant["indoor_tables"] = max(0, int(restaurant.get("indoor_tables", 10)))
            restaurant["outdoor_tables"] = max(0, int(restaurant.get("outdoor_tables", 25)))
            return restaurant
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        pass
    return DEFAULT_RESTAURANT.copy()


def save_restaurant(restaurant: dict, storage_path: str | os.PathLike) -> None:
    target_path = Path(storage_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = DEFAULT_RESTAURANT.copy()
    data.update(restaurant)
    data["service_charge"] = float(data.get("service_charge", 0.0))
    data["indoor_tables"] = max(0, int(data.get("indoor_tables", 10)))
    data["outdoor_tables"] = max(0, int(data.get("outdoor_tables", 25)))
    with target_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)