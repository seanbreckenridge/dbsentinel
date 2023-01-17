from typing import Any
from datetime import datetime, timezone


def to_utc(dt: datetime, tz_aware: bool = False) -> datetime:
    if tz_aware:
        return datetime.fromtimestamp(dt.timestamp(), tz=timezone.utc)
    else:
        return datetime.fromtimestamp(dt.timestamp())


def backoff_handler(details: Any) -> None:
    from mal_id.log import logger

    logger.warning(
        f"backing off after {details.get('tries', '???')} tries, waiting {details.get('wait', '???')}"
    )
