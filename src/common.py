from datetime import datetime


def to_utc(dt: datetime) -> datetime:
    return datetime.fromtimestamp(dt.timestamp())
