from typing import Union

from sqlmodel import Session
from sqlmodel.sql.expression import select
from pydantic import BaseModel
from fastapi import Response

from src.log import logger
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
    assert hasattr(use_model, "id")
    with Session(data_engine) as sess:
        data = sess.exec(
            select(use_model).where(use_model.id == entry_id).limit(1)
        ).first()

    if not data:
        raise ValueError(f"no data for {entry_type} {entry_id}")

    assert isinstance(data, (AnimeMetadata, MangaMetadata))
    return data


class Error(BaseModel):
    error: str


@trouter.get("/refresh_entry")
async def refresh_entry(
    entry_type: EntryType, entry_id: int, response: Response
) -> Union[AnimeMetadata, MangaMetadata, Error]:
    """
    refreshes a single entry in the database
    """
    from app.db_entry_update import refresh_entry as refresh

    logger.info(f"starting refreshing {entry_type} {entry_id}")
    await refresh(
        entry_id=entry_id,
        entry_type=entry_type,
    )
    try:
        response.status_code = 200
        return _fetch_data(entry_type, entry_id)
    except ValueError as ve:
        response.status_code = 404
        return Error(error=str(ve))
