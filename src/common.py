from datetime import datetime

from src.metadata_cache import logger  # noqa: F401


def to_utc(dt: datetime) -> datetime:
    return datetime.fromtimestamp(dt.timestamp())
