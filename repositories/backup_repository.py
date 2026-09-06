import os
import shutil
from datetime import datetime
from pathlib import Path


def create_backup(
    backup_dir: str | os.PathLike,
    files: dict[str, str | os.PathLike],
    keep: int = 30,
) -> Path:
    target_dir = Path(backup_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = target_dir / timestamp
    backup_path.mkdir(parents=True, exist_ok=True)

    for filename, source_path in files.items():
        source = Path(source_path)
        if source.is_file():
            shutil.copy2(source, backup_path / filename)

    backups = list_backups(target_dir)
    for old_backup in backups[keep:]:
        shutil.rmtree(old_backup, ignore_errors=True)
    return backup_path


def list_backups(backup_dir: str | os.PathLike) -> list[Path]:
    target_dir = Path(backup_dir)
    if not target_dir.exists():
        return []
    return sorted(
        (path for path in target_dir.iterdir() if path.is_dir()),
        key=lambda path: path.name,
        reverse=True,
    )


def restore_backup(
    backup_path: str | os.PathLike,
    backup_dir: str | os.PathLike,
    files: dict[str, str | os.PathLike],
) -> None:
    source_dir = Path(backup_path).resolve()
    expected_parent = Path(backup_dir).resolve()
    if not source_dir.is_dir() or source_dir.parent != expected_parent:
        raise ValueError("Invalid backup location")

    for filename, target_path in files.items():
        source_path = source_dir / filename
        if source_path.is_file():
            target = Path(target_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
