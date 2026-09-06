from collections.abc import Callable
from datetime import datetime


class SessionController:
    def __init__(
        self,
        load_orders: Callable[..., list],
        delete_order: Callable[..., float],
    ):
        self._load_orders = load_orders
        self._delete_order = delete_order

    def get_orders(self, now: datetime | None = None) -> list:
        return self._load_orders(now=now or datetime.now())

    def delete_order(self, index: int, now: datetime | None = None) -> float:
        return self._delete_order(index, now=now or datetime.now())
