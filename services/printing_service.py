from pathlib import Path

try:
    from escpos.printer import Win32Raw
except Exception:
    Win32Raw = None

try:
    import win32print
except ImportError:
    win32print = None

try:
    from PIL import Image
except ImportError:
    Image = None


def get_windows_printers() -> list[str]:
    if win32print is None:
        return []
    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [entry[2] for entry in win32print.EnumPrinters(flags)]
    except Exception:
        return []


def get_default_printer() -> str | None:
    if win32print is None:
        return None
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        printers = get_windows_printers()
        return printers[0] if printers else None


def print_with_windows_spooler(text: str, printer_name: str) -> None:
    if win32print is None:
        raise RuntimeError("Windows printing is not available")
    handle = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(handle, 1, ("Restaurant POS receipt", None, "RAW"))
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, text.encode("cp437", errors="replace"))
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)


def _print_image(printer, image_path: str, max_width: int = 576) -> None:
    if Image is None or not image_path or not Path(image_path).is_file():
        return
    image = Image.open(image_path).convert("L")
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize(
            (max_width, max(1, int(image.height * ratio))),
            Image.Resampling.LANCZOS
            if hasattr(Image, "Resampling")
            else Image.ANTIALIAS,
        )
    printer.set(align="center")
    printer.image(image)
    printer.textln("")


def print_with_escpos(
    text: str,
    restaurant: dict,
    printer_name: str | None = None,
) -> tuple[bool, str, None]:
    selected_printer = printer_name or restaurant.get("printer_name") or get_default_printer()
    if not selected_printer:
        return False, "No Windows printer is configured or available.", None

    if Win32Raw is not None:
        try:
            printer = Win32Raw(selected_printer)
            try:
                _print_image(printer, restaurant.get("logo_path", ""))
                printer.set(align="center", bold=True)
                printer.textln(restaurant.get("name", ""))
                printer.set(align="center", bold=False, width=1, height=1)
                printer.textln(restaurant.get("address", ""))
                if restaurant.get("phone"):
                    printer.textln(f"Phone: {restaurant['phone']}")
                if restaurant.get("email"):
                    printer.textln(restaurant["email"])
                printer.textln("-" * 48)
                printer.set(align="left")
                for line in text.splitlines():
                    printer.textln(line)
                _print_image(printer, restaurant.get("footer_path", ""))
                printer.cut()
                return True, "sent to printer", None
            finally:
                printer.close()
        except Exception as printer_error:
            print(f"ESC/POS unavailable on {selected_printer}: {printer_error}")

    try:
        print_with_windows_spooler(text, selected_printer)
        return True, f"sent to printer: {selected_printer}", None
    except Exception as printer_error:
        return False, f"Unable to print on {selected_printer}: {printer_error}", None
