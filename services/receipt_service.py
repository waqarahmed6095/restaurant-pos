import textwrap
from datetime import datetime

from domain.pricing import DEFAULT_SERVICE_CHARGE


def format_currency(value: float) -> str:
    return f"Rs {value:.2f}"


def build_receipt_text(
    order_items: list[dict],
    table_type: str,
    table_number: str,
    include_service_charge: bool = True,
    service_charge: float = DEFAULT_SERVICE_CHARGE,
    order_number: str | None = None,
    restaurant_name: str = "Restaurant",
    restaurant_address: str = "",
    restaurant_phone: str = "",
    restaurant_email: str = "",
) -> str:
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    lines = [restaurant_name]
    if restaurant_address:
        lines.append(restaurant_address)
    if restaurant_phone:
        lines.append(f"Phone: {restaurant_phone}")
    if restaurant_email:
        lines.append(restaurant_email)
    lines.append(f"Date : {now}")
    if order_number:
        lines.append(f"Order No: {order_number}")
    width = 48

    if table_type == "Home Delivery":
        lines.append("Delivery: Home Delivery")
    else:
        lines.append(f"Table: {table_type} {table_number}")

    lines.extend(["=" * width, ""])
    lines.append(f"{'ITEM':<16}{'SIZE':<8}{'QTY':>3}{'UNIT':>10}{'TOTAL':>10}"[:width])
    lines.append("-" * width)

    for item in order_items:
        item_name_lines = textwrap.wrap(
            item["name"], width=16, break_long_words=True, break_on_hyphens=False
        ) or [""]
        size = item["size"][:8]
        qty = str(item["quantity"]).rjust(3)
        unit_price = f"{item['unit_price']:.2f}".rjust(10)
        total = f"{item['total_price']:.2f}".rjust(10)
        lines.append(f"{item_name_lines[0]:<16}{size:<8}{qty:>3}{unit_price:>10}{total:>10}"[:width])
        for continuation in item_name_lines[1:]:
            lines.append(f"{continuation:<16}{'':<8}{'':>3}{'':>10}{'':>10}"[:width])
        lines.append("-" * width)

    lines.extend(["-" * width, ""])
    subtotal = sum(item["total_price"] for item in order_items)
    if include_service_charge and order_items:
        lines.append(f"{'Subtotal:':<16}{format_currency(subtotal):>10}")
        lines.append(f"{'Service Charge:':<16}{format_currency(service_charge):>10}")
    total = subtotal + (service_charge if include_service_charge and order_items else 0.0)
    lines.extend([
        f"{'TOTAL:':<16}{format_currency(total):>10}",
        "=" * width,
        f"Thank you for dining at {restaurant_name}!",
        "",
    ])
    return "\n".join(lines)


def build_kitchen_slip_text(
    order_items: list[dict],
    table_type: str,
    table_number: str,
    order_number: str | None = None,
) -> str:
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
    lines = ["KITCHEN SLIP", f"Date: {now}"]
    if order_number:
        lines.append(f"Order No: {order_number}")
    if table_type == "Home Delivery":
        lines.append("Delivery: Home Delivery")
    else:
        lines.append(f"Table: {table_type} {table_number}")

    lines.extend(["=" * 48, "", f"{'ITEM':<24}{'SIZE':<10}{'QTY':>3}", "-" * 48])
    for item in order_items:
        item_name_lines = textwrap.wrap(
            item["name"], width=24, break_long_words=True, break_on_hyphens=False
        ) or [""]
        size = item["size"][:10]
        qty = str(item["quantity"]).rjust(3)
        lines.append(f"{item_name_lines[0]:<24}{size:<10}{qty:>3}"[:48])
        for continuation in item_name_lines[1:]:
            lines.append(f"{continuation:<24}{'':<10}{'':>3}"[:48])
        lines.append("-" * 48)

    lines.extend(["=" * 48, "Please prepare the items listed above.", ""])
    return "\n".join(lines)
