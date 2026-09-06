from datetime import datetime


def validate_date_range(
    start_date: str | None,
    end_date: str | None,
) -> tuple[str | None, str | None]:
    normalized_start = start_date.strip() if start_date else None
    normalized_end = end_date.strip() if end_date else None
    normalized_start = normalized_start or None
    normalized_end = normalized_end or None

    for value in (normalized_start, normalized_end):
        if value:
            datetime.strptime(value, "%Y-%m-%d")
    if normalized_start and normalized_end and normalized_start > normalized_end:
        raise ValueError("Start date must not be after end date")
    return normalized_start, normalized_end
