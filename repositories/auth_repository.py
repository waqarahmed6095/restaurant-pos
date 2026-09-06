import hashlib
import hmac
import os
from pathlib import Path


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def verify_pin(pin: str, pin_path: str | os.PathLike) -> bool:
    try:
        stored_hash = Path(pin_path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return False
    return hmac.compare_digest(hash_pin(pin), stored_hash)


def save_pin(pin: str, pin_path: str | os.PathLike) -> None:
    target_path = Path(pin_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(hash_pin(pin), encoding="utf-8")
