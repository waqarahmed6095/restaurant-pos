import json
import os
from pathlib import Path


def normalize_menu_item(item: dict) -> dict:
    return {
        "category": str(item.get("category", "")),
        "name": str(item.get("name", "")),
        "size": str(item.get("size", "")),
        "price": float(item.get("price", 0.0)),
    }


def save_menu_items(items: list[dict], storage_path: str | os.PathLike) -> None:
    target_path = Path(storage_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_items = [normalize_menu_item(item) for item in items]
    with target_path.open("w", encoding="utf-8") as handle:
        json.dump(normalized_items, handle, indent=2)


def load_menu_items(
    default_items: list[dict],
    storage_path: str | os.PathLike,
    include_defaults: bool = True,
) -> list[dict]:
    target_path = Path(storage_path)
    if target_path.exists():
        try:
            with target_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                stored_items = [
                    normalize_menu_item(item)
                    for item in data
                    if isinstance(item, dict)
                ]
                if not include_defaults:
                    return stored_items
                stored_by_key = {
                    (item["category"], item["name"], item["size"]): item
                    for item in stored_items
                }
                normalized_defaults = [normalize_menu_item(item) for item in default_items]
                for default_item in normalized_defaults:
                    key = (default_item["category"], default_item["name"], default_item["size"])
                    if key not in stored_by_key:
                        stored_items.append(default_item)
                save_menu_items(stored_items, target_path)
                return stored_items
        except (OSError, json.JSONDecodeError):
            pass

    items = [normalize_menu_item(item) for item in default_items]
    save_menu_items(items, target_path)
    return items
