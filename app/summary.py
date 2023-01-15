from fastapi import Depends, APIRouter
from sqlmodel import Session
from app.db import (
    get_db,
    AnimeMetadata,
    MangaMetadata,
)
from sqlalchemy import select, func

router = APIRouter()


@router.get("/")
async def get_metadata_counts(db: Session = Depends(get_db)):
    anime_status_counts = db.exec(
        select(
            AnimeMetadata.approved_status, func.count(AnimeMetadata.approved_status)  # type: ignore
        ).group_by(AnimeMetadata.approved_status)
    ).all()
    manga_status_counts = db.exec(
        select(
            MangaMetadata.approved_status, func.count(MangaMetadata.approved_status)  # type: ignore
        ).group_by(MangaMetadata.approved_status)
    ).all()
    return {
        "anime": [
            {"status": d["approved_status"], "count": d["count"]}
            for d in anime_status_counts
        ],
        "manga": [
            {"status": d["approved_status"], "count": d["count"]}
            for d in manga_status_counts
        ],
    }
