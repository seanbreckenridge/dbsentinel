import enum
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date

from sqlalchemy import func
from fastapi import Depends, APIRouter
from sqlmodel import Session
from sqlmodel.sql.expression import select
from pydantic import BaseModel, Field

from app.db import (
    get_db,
    AnimeMetadata,
    MangaMetadata,
    Status,
)

router = APIRouter()


class StatusIn(str, enum.Enum):
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    DELETED = "deleted"
    DENIED = "denied"
    ALL = "all"


class QueryModelOut(BaseModel):
    id: int
    title: str
    nsfw: Optional[bool]
    json_data: Dict[str, Any]
    approved_status: Status


class QueryOut(BaseModel):
    entry_type: str = Field(regex="^(anime|manga)$")
    total_count: int
    results: List[QueryModelOut]


class QueryIn(BaseModel):
    title: Optional[str] = Field(min_length=1)
    entry_type: str = Field(default="anime", regex="^(anime|manga)$")
    start_date: Optional[date]
    end_date: Optional[date]
    nsfw: Optional[bool]
    json_data: Optional[Dict[str, Union[str, int, bool]]]
    approved_status: StatusIn = Field(default=StatusIn.ALL)
    order_by: Optional[str] = Field(
        default="id",
        regex="^(id|title|start_date|end_date|approved_status|approved_at|updated_at)$",
    )
    sort: Optional[str] = Field(default="desc", regex="^(asc|desc)$")
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0)


def _serialize_date(dd: date | None) -> Optional[str]:
    if dd is None:
        return None
    return dd.isoformat()


def _serialize_datetime(dd: datetime | None) -> Optional[int]:
    if dd is None:
        return None
    return int(dd.timestamp())


@router.post("/")
async def get_metadata_counts(
    info: QueryIn, sess: Session = Depends(get_db)
) -> QueryOut:
    model = AnimeMetadata if info.entry_type == "anime" else MangaMetadata
    query = select(model)

    if info.title:
        query = query.where(model.title.like(f"%{info.title}%"))  # type: ignore

    if info.start_date is not None:
        query = query.where(model.start_date >= info.start_date)  # type: ignore

    if info.end_date is not None:
        query = query.where(model.end_date <= info.end_date)  # type: ignore

    if info.nsfw is not None:
        query = query.where(model.nsfw == info.nsfw)

    if info.json_data is not None:
        for key, value in info.json_data.items():
            if key == "genres":
                query = query.where(
                    model.json_data["genres"].map(lambda x: x["name"]).contains(value)
                )
            else:
                query = query.where(model.json_data.get(key, None) == value)

    if info.approved_status != StatusIn.ALL:
        query = query.where(model.approved_status == info.approved_status)

    # order/sort
    order_attr = getattr(model, info.order_by)  # type: ignore
    query = query.order_by(
        order_attr.asc() if info.sort == "asc" else order_attr.desc()
    )

    count = sess.exec(select(func.count()).select_from(query.subquery())).first()  # type: ignore
    assert isinstance(count, int)

    if info.offset > count:
        info.offset = 0

    # limit/offset
    query = query.limit(info.limit).offset(info.offset)

    rows = sess.exec(query).all()  # type: ignore

    return QueryOut(
        results=[
            QueryModelOut(
                id=row.id,  # type: ignore
                title=row.title,
                nsfw=row.nsfw,
                json_data={
                    "start_date": _serialize_date(row.start_date),
                    "end_date": _serialize_date(row.end_date),
                    "updated_at": _serialize_datetime(row.updated_at),
                    "approved_at": _serialize_datetime(row.approved_at),
                    **row.json_data,
                },
                approved_status=row.approved_status,
            )
            for row in rows
        ],
        total_count=count,
        entry_type=info.entry_type,
    )
