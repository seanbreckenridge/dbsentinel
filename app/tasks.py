from typing import Dict, Any, List, Union
from datetime import datetime
from asyncio import sleep

from src.log import logger

from fastapi import APIRouter, Depends
from sqlalchemy import select
from pydantic import BaseModel
from sqlmodel import Session

from app.db import (
    EntryType,
    get_db,
    data_engine,
    AnimeMetadata,
    MangaMetadata,
)

router = APIRouter()


@router.get("/full_database_update")
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
            sess.exec(select(use_model).where(use_model.id == entry_id).limit(1))
        )
    assert type(data[0]) in {AnimeMetadata, MangaMetadata}
    return data[0]


from asyncio import Lock

# TODO: does this actually work here, look into fastapi??
REFRESH_LOCK = Lock()


@router.get("/refresh_entry")
async def refresh_entry(
    entry_type: EntryType, entry_id: int
) -> Union[AnimeMetadata, MangaMetadata]:
    """
    adds a request to update an entry to the database
    """
    from .db_entry_update import refresh_entry

    async with REFRESH_LOCK:
        logger.info(f"starting refreshing {entry_type} {entry_id}")
        await refresh_entry(
            entry_id=entry_id,
            entry_type=entry_type,
        )
    return _fetch_data(entry_type, entry_id)
