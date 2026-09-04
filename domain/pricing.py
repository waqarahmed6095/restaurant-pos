from collections.abc import Iterable


DEFAULT_SERVICE_CHARGE = 30.0


def calculate_order_total(
    items: Iterable[object],
    include_service_charge: bool = True,
    service_charge: float = DEFAULT_SERVICE_CHARGE,
) -> float:
    subtotal = sum(
        float(item.total_price if hasattr(item, "total_price") else item["total_price"])
        for item in items
    )
    if include_service_charge and subtotal:
        return subtotal + service_charge
    return subtotal


def get_categories(menu_items: Iterable[dict]) -> list[str]:
    return sorted({item["category"] for item in menu_items})


def get_items_for_category(menu_items: Iterable[dict], category: str) -> list[str]:
    return sorted({item["name"] for item in menu_items if item["category"] == category})


def get_sizes_for_item(menu_items: Iterable[dict], item_name: str) -> list[str]:
    return [item["size"] for item in menu_items if item["name"] == item_name]


def get_price_for_item(menu_items: Iterable[dict], item_name: str, size: str) -> float:
    for item in menu_items:
        if item["name"] == item_name and item["size"] == size:
            return float(item["price"])
    raise LookupError(f"No menu item found for {item_name!r} ({size!r})")
