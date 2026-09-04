from dataclasses import dataclass


@dataclass(frozen=True)
class MenuItem:
    category: str
    name: str
    size: str
    price: float


@dataclass
class OrderItem:
    name: str
    size: str
    quantity: int
    unit_price: float

    @property
    def total_price(self) -> float:
        return self.unit_price * self.quantity


@dataclass
class Order:
    items: list[OrderItem]
    table_type: str = "Indoor"
    table_number: str = "1"
    include_service_charge: bool = True

    @property
    def subtotal(self) -> float:
        return sum(item.total_price for item in self.items)
