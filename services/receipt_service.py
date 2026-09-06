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
        lines.append(
            f"{item_name_lines[0]:<16}{size:<8}{qty:>3}{unit_price:>10}{total:>10}"[
                :width
            ]
        )
        for continuation in item_name_lines[1:]:
            lines.append(f"{continuation:<16}{'':<8}{'':>3}{'':>10}{'':>10}"[:width])
        lines.append("-" * width)

    lines.extend(["-" * width, ""])
    subtotal = sum(item["total_price"] for item in order_items)
    if include_service_charge and order_items:
        lines.append(f"{'Subtotal:':<16}{format_currency(subtotal):>10}")
        lines.append(f"{'Service Charge:':<16}{format_currency(service_charge):>10}")
    total = subtotal + (
        service_charge if include_service_charge and order_items else 0.0
    )
    lines.extend(
        [
            f"{'TOTAL:':<16}{format_currency(total):>10}",
            "=" * width,
            f"Thank you for dining at {restaurant_name}!",
            "",
        ]
    )
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


def build_closing_report_text(
    orders: list[dict],
    session_id: str,
    restaurant_name: str = "Restaurant",
    service_charge: float = 0.0,
) -> str:
    width = 48
    subtotal = 0.0
    applied_service_charge = 0.0
    total = 0.0

    lines = [
        restaurant_name.center(width),
        "END OF DAY REPORT".center(width),
        f"Session: {session_id}",
        f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
        "=" * width,
        "",
        f"{'Tickets:':<24}{len(orders):>24}",
        "",
        f"{'Order':<16}{'Items':>8}{'Total':>24}",
        "-" * width,
    ]

    for index, order in enumerate(orders, start=1):
        order_items = order.get("items", []) or []
        order_subtotal = sum(
            float(item.get("total", item.get("total_price", 0.0)))
            for item in order_items
        )
        order_total = float(order.get("total", order.get("amount", order_subtotal)))
        order_service_charge = max(0.0, order_total - order_subtotal)
        if not order.get("include_service_charge", bool(order_service_charge)):
            order_service_charge = 0.0
        if order_service_charge == 0.0 and order.get("include_service_charge"):
            order_service_charge = min(
                service_charge, max(0.0, order_total - order_subtotal)
            )

        order_number = str(order.get("order_number", f"#{index}"))[:16]
        lines.append(
            f"{order_number:<16}{len(order_items):>8}{format_currency(order_total):>24}"[
                :width
            ]
        )
        subtotal += order_subtotal
        applied_service_charge += order_service_charge
        total += order_total

    lines.extend(
        [
            "-" * width,
            f"{'Subtotal:':<24}{format_currency(subtotal):>24}",
            f"{'Service Charge:':<24}{format_currency(applied_service_charge):>24}",
            f"{'TOTAL:':<24}{format_currency(total):>24}",
            "=" * width,
            "Closeout is a report only; orders remain stored.",
            "",
        ]
    )
    return "\n".join(lines)
