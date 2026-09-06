import logging
from pathlib import Path


def configure_logging(data_dir: Path) -> logging.Logger:
    data_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("restaurant_pos")
    if not logger.handlers:
        handler = logging.FileHandler(data_dir / "app.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
