def create_order_item(
    name: str,
    size: str,
    quantity: int,
    unit_price: float,
) -> dict:
    return {
        "name": name,
        "size": size,
        "quantity": quantity,
        "unit_price": float(unit_price),
        "total_price": float(unit_price) * quantity,
    }


def serialize_order_items(order_items: list[dict]) -> list[dict]:
    return [
        {
            "name": item["name"],
            "size": item["size"],
            "qty": item["quantity"],
            "unit_price": item["unit_price"],
            "total": item["total_price"],
        }
        for item in order_items
    ]


def deserialize_order_items(items: list[dict]) -> list[dict]:
    restored = []
    for item in items or []:
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
        restored.append(
            create_order_item(
                str(item.get("name", "")),
                str(item.get("size", "")),
                quantity,
                float(unit_price),
            )
            | {"total_price": float(total_price)}
        )
    return restored
