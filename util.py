from datetime import datetime


def xcal_format_duration(start: datetime, end: datetime) -> str:
    seconds = int((end - start).total_seconds())

    days = seconds // (24 * 60 * 60)
    seconds = seconds % (24 * 60 * 60)

    hours = seconds // (60 * 60)
    seconds = seconds % (60 * 60)

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{days}:{hours:02}:{minutes:02}:{seconds:02}"
