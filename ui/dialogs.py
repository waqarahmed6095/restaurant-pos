from collections.abc import Callable
from tkinter import messagebox


def show_session_sales(parent, amount: float, format_currency: Callable[[float], str]) -> None:
    messagebox.showinfo(
        "Session Sales",
        f"Session Sales: {format_currency(amount)}",
        parent=parent,
    )
