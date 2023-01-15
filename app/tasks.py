from typing import Union

from src.log import logger

from sqlalchemy import select
from sqlmodel import Session

from app.db import (
    EntryType,
    data_engine,
    AnimeMetadata,
    MangaMetadata,
)
from app.threaded_router import ThreadedRouter

# each route only allows one connection to be made at a time
# to rate limit requests to MAL
# and prevent full_update from corrupting the db while its already running
trouter = ThreadedRouter()


@trouter.get("/full_database_update")
async def full_update() -> str:
    """
    this is expensive! -- only do this when necessary

    happens once every 10 minutes, pinged from the ./update_data script
    after other stuff has been updated
    """
    from app.db_entry_update import update_database

    await update_database()

    return "done with db update"


def _fetch_data(
    entry_type: EntryType, entry_id: int
) -> Union[AnimeMetadata, MangaMetadata]:
    use_model = AnimeMetadata if entry_type == "anime" else MangaMetadata
    with Session(data_engine) as sess:
        data = list(
            sess.exec(select(use_model).where(use_model.id == entry_id).limit(1))  # type: ignore
        )
    item = data[0][0]
    assert type(item) in {AnimeMetadata, MangaMetadata}
    return item


@trouter.get("/refresh_entry")
async def refresh_entry(
    entry_type: EntryType, entry_id: int
) -> Union[AnimeMetadata, MangaMetadata]:
    """
    adds a request to update an entry to the database
    """
    from .db_entry_update import refresh_entry

    logger.info(f"starting refreshing {entry_type} {entry_id}")
    await refresh_entry(
        entry_id=entry_id,
        entry_type=entry_type,
    )
    return _fetch_data(entry_type, entry_id)
