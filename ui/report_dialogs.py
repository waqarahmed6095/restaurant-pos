import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk


def open_closing_report(
    parent,
    session_id: str,
    orders: list[dict],
    report_text: str,
    colors: dict,
    print_report,
):
    report_window = tk.Toplevel(parent)
    report_window.title(f"End-of-day report - {session_id}")
    report_window.geometry("620x720")
    report_window.minsize(520, 560)
    report_window.transient(parent)
    report_window.configure(bg=colors["canvas"])

    ctk.CTkLabel(
        report_window,
        text="End-of-day closing report",
        text_color=colors["ink"],
        font=("Segoe UI", 21, "bold"),
    ).pack(anchor="w", padx=18, pady=(18, 2))
    ctk.CTkLabel(
        report_window,
        text=f"Session {session_id}  ·  {len(orders)} ticket(s)",
        text_color=colors["muted"],
        font=("Segoe UI", 10),
    ).pack(anchor="w", padx=18, pady=(0, 12))

    text_area = tk.Text(
        report_window,
        wrap="none",
        padx=14,
        pady=14,
        font=("Courier New", 10),
        bg=colors["panel"],
        fg=colors["ink"],
        relief="flat",
    )
    text_area.insert("1.0", report_text)
    text_area.configure(state="disabled")
    text_area.pack(fill="both", expand=True, padx=18, pady=(0, 12))

    action_frame = ctk.CTkFrame(report_window, fg_color="transparent")
    action_frame.pack(fill="x", padx=18, pady=(0, 18))

    def export_report():
        target = filedialog.asksaveasfilename(
            parent=report_window,
            title="Export closing report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
        )
        if not target:
            return
        Path(target).write_text(report_text, encoding="utf-8")
        messagebox.showinfo("Closing report", "The closing report was exported.", parent=report_window)

    def start_print():
        def worker():
            success, message, _ = print_report(report_text)
            report_window.after(
                0,
                lambda: messagebox.showinfo(
                    "Closing report" if success else "Print error",
                    message,
                    parent=report_window,
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    ctk.CTkButton(
        action_frame,
        text="Export report",
        command=export_report,
        height=38,
        fg_color=colors["soft"],
        hover_color=colors["line"],
        text_color=colors["ink"],
    ).pack(side="left", expand=True, fill="x", padx=(0, 6))
    ctk.CTkButton(
        action_frame,
        text="Print report",
        command=start_print,
        height=38,
        fg_color=colors["brand"],
        hover_color=colors["brand_dark"],
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left", expand=True, fill="x", padx=(6, 0))

    return report_window


def open_sales_analytics(parent, colors, get_analytics, format_currency, validate_range):
    window = tk.Toplevel(parent)
    window.title("Sales analytics")
    window.geometry("760x620")
    window.minsize(640, 480)
    window.transient(parent)
    window.configure(bg=colors["canvas"])
    window.columnconfigure(0, weight=1)
    window.rowconfigure(2, weight=1)

    ctk.CTkLabel(window, text="Sales analytics", text_color=colors["ink"], font=("Segoe UI", 21, "bold")).grid(
        row=0, column=0, sticky="w", padx=18, pady=(18, 2)
    )
    ctk.CTkLabel(
        window,
        text="See which menu items sell most and generate the most revenue.",
        text_color=colors["muted"],
        font=("Segoe UI", 10),
    ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

    frame = ctk.CTkFrame(window, fg_color=colors["panel"], corner_radius=10)
    frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(1, weight=1)
    controls = ctk.CTkFrame(frame, fg_color="transparent")
    controls.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
    start_var, end_var = tk.StringVar(), tk.StringVar()
    ttk.Label(controls, text="From (YYYY-MM-DD)").pack(side="left", padx=(0, 4))
    ttk.Entry(controls, textvariable=start_var, width=14).pack(side="left", padx=(0, 10))
    ttk.Label(controls, text="To (YYYY-MM-DD)").pack(side="left", padx=(0, 4))
    ttk.Entry(controls, textvariable=end_var, width=14).pack(side="left", padx=(0, 10))
    tree = ttk.Treeview(frame, columns=("item", "size", "quantity", "revenue"), show="headings", style="Modern.Treeview")
    for column, heading in (("item", "Item"), ("size", "Size"), ("quantity", "Qty sold"), ("revenue", "Revenue")):
        tree.heading(column, text=heading)
    tree.column("item", width=320, anchor="w")
    tree.column("size", width=130, anchor="w")
    tree.column("quantity", width=100, anchor="center")
    tree.column("revenue", width=130, anchor="e")
    tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))
    tree.configure(yscrollcommand=scrollbar.set)
    summary = ctk.CTkLabel(frame, text="0 items sold  ·  Revenue: Rs 0.00", text_color=colors["brand"], font=("Segoe UI", 12, "bold"))
    summary.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))

    def refresh():
        try:
            start, end = validate_range(start_var.get(), end_var.get())
        except ValueError:
            messagebox.showerror("Sales analytics", "Enter a valid date range in YYYY-MM-DD format.", parent=window)
            return
        data = get_analytics(start_date=start, end_date=end)
        for row in tree.get_children():
            tree.delete(row)
        quantity = sum(int(item["quantity"]) for item in data)
        revenue = sum(float(item["revenue"]) for item in data)
        for item in data:
            tree.insert("", "end", values=(item["name"], item["size"], item["quantity"], format_currency(item["revenue"])))
        if not data:
            tree.insert("", "end", values=("No item sales recorded", "", "", ""))
        summary.configure(text=f"{quantity} items sold  ·  Revenue: {format_currency(revenue)}")

    ctk.CTkButton(controls, text="Refresh", command=refresh, width=90, height=32, fg_color=colors["brand"], hover_color=colors["brand_dark"]).pack(side="left")
    refresh()
    return window


def open_sales_report(parent, colors, get_report, format_currency, validate_range):
    window = tk.Toplevel(parent)
    window.title("Sales Report")
    window.geometry("900x650")
    window.minsize(620, 420)
    window.transient(parent)
    window.configure(bg=colors["canvas"])
    window.columnconfigure(0, weight=1)
    window.rowconfigure(2, weight=1)
    ctk.CTkLabel(window, text="Sales report", text_color=colors["ink"], font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
    ctk.CTkLabel(window, text="Review session totals or filter by date range.", text_color=colors["muted"], font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))
    filters = ctk.CTkFrame(window, fg_color=colors["panel"], corner_radius=10)
    filters.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))
    filters.columnconfigure(0, weight=1)
    filters.rowconfigure(1, weight=1)
    controls = ctk.CTkFrame(filters, fg_color="transparent")
    controls.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
    start_var, end_var = tk.StringVar(), tk.StringVar()
    ttk.Label(controls, text="From (YYYY-MM-DD)").pack(side="left", padx=(0, 4))
    ttk.Entry(controls, textvariable=start_var, width=14).pack(side="left", padx=(0, 8))
    ttk.Label(controls, text="To (YYYY-MM-DD)").pack(side="left", padx=(0, 4))
    ttk.Entry(controls, textvariable=end_var, width=14).pack(side="left", padx=(0, 8))
    tree = ttk.Treeview(filters, columns=("date", "orders", "total"), show="headings", style="Modern.Treeview")
    for column, heading in (("date", "Session date"), ("orders", "Orders"), ("total", "Total sales")):
        tree.heading(column, text=heading)
    tree.column("date", width=240, anchor="w")
    tree.column("orders", width=120, anchor="center")
    tree.column("total", width=180, anchor="e")
    tree.grid(row=1, column=0, sticky="nsew", padx=(16, 0), pady=(0, 6))
    scrollbar = ttk.Scrollbar(filters, orient="vertical", command=tree.yview)
    scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 16), pady=(0, 6))
    tree.configure(yscrollcommand=scrollbar.set)
    summary = ctk.CTkLabel(filters, text="Grand total: Rs 0.00", text_color=colors["brand"], font=("Segoe UI", 14, "bold"))
    summary.grid(row=2, column=0, columnspan=2, sticky="e", padx=16, pady=(2, 6))

    def refresh():
        try:
            start, end = validate_range(start_var.get(), end_var.get())
        except ValueError:
            messagebox.showerror("Sales report", "Enter a valid date range in YYYY-MM-DD format.", parent=window)
            return
        data = get_report(start_date=start, end_date=end)
        for row in tree.get_children():
            tree.delete(row)
        total = sum(entry["total"] for entry in data)
        for entry in data:
            tree.insert("", "end", values=(entry["session_id"], entry["order_count"], format_currency(entry["total"])))
        if not data:
            tree.insert("", "end", values=("No sales recorded", "", format_currency(0.0)))
        summary.configure(text=f"Grand total: {format_currency(total)}")

    ctk.CTkButton(controls, text="Filter", command=refresh, width=90, height=32, fg_color=colors["brand"], hover_color=colors["brand_dark"]).pack(side="left")
    refresh()
    return window
