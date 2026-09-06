class OrderController:
    def __init__(self):
        self.items: list[dict] = []

    def add_item(self, name: str, size: str, quantity: int, unit_price: float) -> dict:
        item = {
            "name": name,
            "size": size,
            "quantity": quantity,
            "unit_price": float(unit_price),
            "total_price": float(unit_price) * quantity,
        }
        self.items.append(item)
        return item

    def remove_item(self, index: int) -> None:
        self.items.pop(index)

    def clear(self) -> None:
        self.items.clear()

    def replace(self, items: list[dict]) -> None:
        self.items[:] = items

    def total(self, include_service_charge: bool, service_charge: float) -> float:
        subtotal = sum(item["total_price"] for item in self.items)
        return subtotal + service_charge if include_service_charge and self.items else 0.0
