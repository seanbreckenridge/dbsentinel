from typing import Union

from sqlmodel import Session
from sqlmodel.sql.expression import select
from pydantic import BaseModel
from fastapi import Response, APIRouter

from mal_id.log import logger
from mal_id.metadata_cache import has_metadata
from app.db import (
    EntryType,
    data_engine,
    AnimeMetadata,
    MangaMetadata,
)

router = APIRouter()


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


def _has_data(entry_type: EntryType, entry_id: int) -> bool:
    return has_metadata(entry_id, entry_type.value.lower())


class Error(BaseModel):
    error: str


@router.get("/refresh_entry")
async def refresh_entry(
    entry_type: EntryType, entry_id: int, response: Response
) -> Union[AnimeMetadata, MangaMetadata, Error]:
    """
    refreshes a single entry in the database
    """
    from app.db_entry_update import refresh_entry as refresh

    logger.info(f"refreshing {entry_type} {entry_id}")
    if not _has_data(entry_type, entry_id):
        logger.error(f"no data for {entry_type} {entry_id}, can't refresh")
        response.status_code = 400
        return Error(error="That id does not have any data saved, can't refresh")

    await refresh(
        entry_id=entry_id,
        entry_type=entry_type.value.lower(),
    )
    try:
        response.status_code = 200
        return _fetch_data(entry_type, entry_id)
    except ValueError as ve:
        response.status_code = 404
        return Error(error=str(ve))
