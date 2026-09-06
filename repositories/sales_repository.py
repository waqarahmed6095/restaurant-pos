import json
import os
from datetime import datetime, timedelta
from pathlib import Path


def get_session_id(now: datetime | None = None) -> str | None:
    current_time = now or datetime.now()
    if current_time.hour >= 17:
        return current_time.strftime("%Y-%m-%d")
    if current_time.hour <= 3:
        return (current_time - timedelta(days=1)).strftime("%Y-%m-%d")
    return None


def _load_data(storage_path: str | os.PathLike) -> dict:
    target_path = Path(storage_path)
    if not target_path.exists():
        return {}
    try:
        with target_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_data(data: dict, storage_path: str | os.PathLike) -> None:
    target_path = Path(storage_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def get_session_sales(
    storage_path: str | os.PathLike, now: datetime | None = None
) -> float:
    session_id = get_session_id(now)
    if session_id is None:
        return 0.0
    value = _load_data(storage_path).get(session_id, 0.0)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        return float(value.get("total", 0.0))
    return 0.0


def get_session_orders(
    storage_path: str | os.PathLike, now: datetime | None = None
) -> list:
    session_id = get_session_id(now)
    if session_id is None:
        return []
    value = _load_data(storage_path).get(session_id)
    if isinstance(value, dict):
        return value.get("orders", []) or []
    return []


def get_sales_report(
    storage_path: str | os.PathLike,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    report = []
    for session_id, value in _load_data(storage_path).items():
        session_id = str(session_id)
        if start_date and session_id < start_date:
            continue
        if end_date and session_id > end_date:
            continue
        if isinstance(value, (int, float)):
            total = float(value)
            order_count = 0
        elif isinstance(value, dict):
            try:
                total = float(value.get("total", 0.0))
            except (TypeError, ValueError):
                total = 0.0
            orders = value.get("orders", [])
            order_count = len(orders) if isinstance(orders, list) else 0
        else:
            continue
        report.append(
            {"session_id": session_id, "order_count": order_count, "total": total}
        )
    return sorted(report, key=lambda entry: entry["session_id"], reverse=True)


def get_sales_analytics(
    storage_path: str | os.PathLike,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    totals: dict[tuple[str, str], dict] = {}
    for session_id, value in _load_data(storage_path).items():
        session_id = str(session_id)
        if start_date and session_id < start_date:
            continue
        if end_date and session_id > end_date:
            continue
        if not isinstance(value, dict):
            continue

        for order in value.get("orders", []) or []:
            if not isinstance(order, dict):
                continue
            for item in order.get("items", []) or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip() or "Unknown item"
                size = str(item.get("size", "")).strip()
                key = (name, size)
                summary = totals.setdefault(
                    key,
                    {"name": name, "size": size, "quantity": 0, "revenue": 0.0},
                )
                try:
                    quantity = int(item.get("qty", item.get("quantity", 1)))
                except (TypeError, ValueError):
                    quantity = 0
                try:
                    revenue = float(
                        item.get(
                            "total",
                            item.get("total_price", item.get("amount", 0.0)),
                        )
                    )
                except (TypeError, ValueError):
                    revenue = 0.0
                summary["quantity"] += quantity
                summary["revenue"] += revenue

    return sorted(
        totals.values(),
        key=lambda entry: (-entry["revenue"], entry["name"].casefold(), entry["size"].casefold()),
    )


def get_next_order_number(
    storage_path: str | os.PathLike,
    now: datetime | None = None,
    replace_index: int | None = None,
) -> str:
    session_id = get_session_id(now)
    if session_id is None:
        return ""
    orders = get_session_orders(storage_path, now)
    if replace_index is not None and 0 <= replace_index < len(orders):
        existing_number = orders[replace_index].get("order_number")
        if existing_number:
            return str(existing_number)
    highest = 0
    prefix = f"{session_id}-"
    for order in orders:
        value = str(order.get("order_number", ""))
        if value.startswith(prefix):
            try:
                highest = max(highest, int(value[len(prefix) :]))
            except ValueError:
                continue
    return f"{prefix}{highest + 1:03d}"


def record_session_order(
    order: dict,
    storage_path: str | os.PathLike,
    now: datetime | None = None,
    replace_index: int | None = None,
) -> float:
    session_id = get_session_id(now)
    if session_id is None:
        return 0.0

    data = _load_data(storage_path)
    existing = data.get(session_id)
    if isinstance(existing, (int, float)):
        existing = {"total": float(existing), "orders": []}
    if not isinstance(existing, dict):
        existing = {"total": 0.0, "orders": []}

    order_copy = dict(order)
    order_copy.setdefault("timestamp", (now or datetime.now()).isoformat())
    order_copy.setdefault(
        "order_number", get_next_order_number(storage_path, now, replace_index)
    )
    orders = existing.setdefault("orders", [])
    if replace_index is not None and 0 <= replace_index < len(orders):
        previous_total = float(
            orders[replace_index].get("total", orders[replace_index].get("amount", 0.0))
        )
        orders[replace_index] = order_copy
        existing["total"] = (
            float(existing.get("total", 0.0))
            - previous_total
            + float(order_copy.get("total", order_copy.get("amount", 0.0)))
        )
    else:
        orders.append(order_copy)
        existing["total"] = float(existing.get("total", 0.0)) + float(
            order_copy.get("total", order_copy.get("amount", 0.0))
        )

    data[session_id] = existing
    _save_data(data, storage_path)
    return float(existing["total"])


def record_session_sale(
    amount: float, storage_path: str | os.PathLike, now: datetime | None = None
) -> float:
    return record_session_order({"total": float(amount)}, storage_path, now)


def delete_session_order(
    index: int, storage_path: str | os.PathLike, now: datetime | None = None
) -> float:
    session_id = get_session_id(now)
    if session_id is None:
        return 0.0

    data = _load_data(storage_path)
    existing = data.get(session_id)
    if not isinstance(existing, dict):
        return 0.0
    orders = existing.get("orders") or []
    if not isinstance(orders, list) or index < 0 or index >= len(orders):
        return 0.0

    orders.pop(index)
    existing["orders"] = orders
    existing["total"] = sum(
        float(order.get("total", order.get("amount", 0.0))) for order in orders
    )
    data[session_id] = existing
    _save_data(data, storage_path)
    return float(existing["total"])
