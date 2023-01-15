from typing import List

from fastapi import Depends, APIRouter
from sqlmodel import Session
from sqlmodel.sql.expression import select
from sqlalchemy import func
from pydantic import BaseModel, root_validator

from app.db import (
    get_db,
    AnimeMetadata,
    MangaMetadata,
)

router = APIRouter()


class Status(BaseModel):
    status: str
    count: int

    @root_validator(pre=True)
    def rename_status(cls, values):
        if "approved_status" in values:
            values["status"] = values.pop("approved_status")
        return values


class MetadataCountOut(BaseModel):
    anime: List[Status]
    manga: List[Status]


@router.get("/", response_model=MetadataCountOut)
async def get_metadata_counts(db: Session = Depends(get_db)) -> MetadataCountOut:
    anime_status_counts = db.exec(
        select(AnimeMetadata.approved_status, func.count(AnimeMetadata.approved_status))  # type: ignore[call-overload]
        .group_by(AnimeMetadata.approved_status)
        .order_by(AnimeMetadata.approved_status)
    ).all()
    manga_status_counts = db.exec(
        select(MangaMetadata.approved_status, func.count(MangaMetadata.approved_status))  # type: ignore[call-overload]
        .group_by(MangaMetadata.approved_status)
        .order_by(MangaMetadata.approved_status)
    ).all()
    return MetadataCountOut(
        anime=anime_status_counts,
        manga=manga_status_counts,
    )
