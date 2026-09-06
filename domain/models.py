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


@dataclass
class RestaurantProfile:
    name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    logo_path: str = ""
    app_icon_path: str = ""
    footer_path: str = ""
    printer_name: str = ""
    service_charge: float = 0.0
    indoor_tables: int = 10
    outdoor_tables: int = 25
