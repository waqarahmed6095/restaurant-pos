import re
from pathlib import Path


PHONE_PATTERN = re.compile(r"[+()\d][\d\s().-]{6,19}")
EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


def validate_contact(phone: str, email: str) -> str | None:
    if not phone or not PHONE_PATTERN.fullmatch(phone):
        return "Enter a valid phone number."
    if email and not EMAIL_PATTERN.fullmatch(email):
        return "Enter a valid email address."
    return None


def validate_image_path(path: str, extensions: set[str], label: str) -> str | None:
    if not path:
        return None
    target = Path(path)
    if not target.is_file() or target.suffix.lower() not in extensions:
        return f"Choose a valid {label.lower()} file."
    return None


def validate_non_negative_number(value: str, label: str, maximum: float | None = None) -> tuple[float | None, str | None]:
    try:
        number = float(value or 0)
    except ValueError:
        return None, f"Enter a valid {label.lower()}."
    if number < 0 or maximum is not None and number > maximum:
        return None, f"{label} must be between 0 and {maximum}." if maximum is not None else f"{label} cannot be negative."
    return number, None
