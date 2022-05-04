from typing import Any
from datetime import datetime


def to_utc(dt: datetime) -> datetime:
    return datetime.fromtimestamp(dt.timestamp())


def backoff_handler(details: Any) -> None:
    from src.log import logger

    logger.warning(
        f"backing off after {details.get('tries', '???')} tries, waiting {details.get('wait', '???')}"
    )
