import enum
from typing import List, Optional, Dict, Any, Union
from datetime import date

from sqlalchemy import func
from fastapi import Depends, APIRouter, HTTPException
from sqlmodel import Session
from sqlmodel.sql.expression import select
from pydantic import BaseModel, Field

from mal_id.log import logger
from app.db import (
    get_db,
    ApprovedBase,
    AnimeMetadata,
    ProxiedImage,
    EntryType,
    MangaMetadata,
    Status,
)

from app.db_entry_update import _get_img_url

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
    image_url: Optional[str]
    alternate_titles: Dict[str, Any]
    json_data: Dict[str, Any]
    media_type: Optional[str]
    approved_status: Status
    member_count: Optional[int]
    average_episode_duration: Optional[int]
    metadata_updated_at: float
    status_updated_at: float
    start_date: str | None
    end_date: str | None


class QueryOut(BaseModel):
    entry_type: EntryType
    total_count: int
    results: List[QueryModelOut]


class QueryInOrderBy(str, enum.Enum):
    ID = "id"
    TITLE = "title"
    START_DATE = "start_date"
    END_DATE = "end_date"
    STATUS_UPDATED_AT = "status_updated_at"
    METADATA_UPDATED_AT = "metadata_updated_at"
    MEMBER_COUNT = "member_count"
    AVERAGE_EPISODE_DURATION = "average_episode_duration"


class QueryInSort(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


class QueryIn(BaseModel):
    title: Optional[str] = Field(min_length=1)
    entry_type: EntryType = Field(default=EntryType.ANIME)
    media_type: Optional[str]
    nsfw: Optional[bool]
    json_data: Optional[Dict[str, Union[str, int, bool]]]
    approved_status: StatusIn = Field(default=StatusIn.ALL)
    order_by: QueryInOrderBy = Field(default=QueryInOrderBy.ID)
    sort: QueryInSort = Field(default=QueryInSort.DESC)
    limit: int = Field(default=100, le=250)
    offset: int = Field(default=0)


def _serialize_date(dd: date | None) -> Optional[str]:
    if dd is None:
        return None
    return dd.isoformat()


APPROVED_KEYS = {
    "num_episodes",
    "chapters",
    "volumes",
}


# dont just mirror all data for approved entries, just link to the page
def _filter_keys_for_status(d: Dict[str, Any], status: Status) -> Dict[str, Any]:
    if status == Status.APPROVED:
        return {k: d[k] for k in d if k in APPROVED_KEYS}
    else:
        return d


def _pick_image(metadata: ApprovedBase, proxied: ProxiedImage | None) -> Optional[str]:
    if proxied is None:
        return _get_img_url(metadata.json_data.get("main_picture", {}))
    if metadata.approved_status == Status.APPROVED:
        return proxied.mal_url
    else:
        return proxied.proxied_url


@router.post("/")
async def media_query(info: QueryIn, sess: Session = Depends(get_db)) -> QueryOut:
    logger.info(f"query: {info}")
    model = AnimeMetadata if info.entry_type == EntryType.ANIME else MangaMetadata
    entry_type = EntryType.from_str(info.entry_type)

    # left join on proxied image
    query = select(model, ProxiedImage).join(
        ProxiedImage,
        (model.id == ProxiedImage.mal_id) & (ProxiedImage.mal_entry_type == entry_type),
        isouter=True,
    )

    if info.title:
        query = query.where(model.title.like(f"%{info.title}%"))  # type: ignore

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

    if info.media_type is not None:
        query = query.where(model.media_type == info.media_type)

    if info.approved_status != StatusIn.ALL:
        query = query.where(model.approved_status == info.approved_status)

    # order/sort
    order_attr = {
        "id": model.id,
        "title": model.title,
        "start_date": model.start_date,
        "end_date": model.end_date,
        "status_updated_at": model.status_changed_at,
        "metadata_updated_at": model.updated_at,
        "member_count": model.member_count,
        "average_episode_duration": model.average_episode_duration,
    }.get(info.order_by, model.id)
    query = query.order_by(order_attr.desc() if info.sort == "desc" else order_attr.asc())  # type: ignore

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
                image_url=_pick_image(row, image),
                media_type=row.media_type,
                alternate_titles=row.json_data.get("alternative_titles", {}),
                metadata_updated_at=row.updated_at.timestamp(),
                status_updated_at=row.status_changed_at.timestamp(),
                start_date=_serialize_date(row.start_date),
                end_date=_serialize_date(row.end_date),
                json_data=_filter_keys_for_status(row.json_data, row.approved_status),
                member_count=row.member_count,
                average_episode_duration=row.average_episode_duration,
                approved_status=row.approved_status,
            )
            for row, image in rows
        ],
        total_count=count,
        entry_type=info.entry_type,
    )


class ByIdQueryIn(BaseModel):
    id: int
    entry_type: EntryType


class ByIdRawOut(BaseModel):
    id: int
    proxied_image: str
    json_data: dict


@router.post("/id/")
async def media_query_by_id(
    info: ByIdQueryIn, sess: Session = Depends(get_db)
) -> ByIdRawOut:
    model = AnimeMetadata if info.entry_type == EntryType.ANIME else MangaMetadata
    entry_type = EntryType.from_str(info.entry_type)

    # left join on proxied image
    query = select(model, ProxiedImage).join(
        ProxiedImage,
        (model.id == ProxiedImage.mal_id) & (ProxiedImage.mal_entry_type == entry_type),
        isouter=True,
    )

    query = query.where(model.id == info.id)
    query = query.limit(1)
    res = list(sess.exec(query).all())

    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Entry not found")

    row, image = res[0]

    json_data = row.json_data
    json_data["title"] = row.title
    json_data["nsfw"] = row.nsfw
    json_data["approved_status"] = row.approved_status
    json_data["media_type"] = row.media_type
    json_data["member_count"] = row.member_count
    json_data["status_updated_at"] = row.status_changed_at.timestamp()
    json_data["metadata_updated_at"] = row.updated_at.timestamp()
    json_data["start_date"] = _serialize_date(row.start_date)
    json_data["end_date"] = _serialize_date(row.end_date)

    if info.entry_type == EntryType.ANIME:
        json_data["average_episode_duration"] = row.average_episode_duration

    return ByIdRawOut(
        id=row.id,
        title=row.title,
        proxied_image=image.proxied_url if image else None,
        json_data=row.json_data,
    )
