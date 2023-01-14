import enum
from typing import Iterator, Optional, Set, Dict, Any
from datetime import datetime, date, timezone

from urllib.parse import urlparse
from malexport.parse.common import parse_date_safe
from sqlalchemy import update
from sqlmodel import SQLModel, Field, create_engine, Session, Column, JSON
from url_cache.core import Summary

from src.metadata_cache import request_metadata
from src.linear_history import read_linear_history
from src.ids import approved_ids, unapproved_ids
from src.log import logger
from src.paths import sqlite_db_uri

from app.settings import settings


class Status(str, enum.Enum):
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    DELETED = "deleted"


class ApprovedData(SQLModel, table=False):
    # approved status of the entry
    approved_status: Status = Field(default=Status.UNAPPROVED)
    approved_at: Optional[datetime] = Field(default=None)


class AnimeMetadata(ApprovedData, table=True):
    id: int = Field(primary_key=True)
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    nsfw: bool = Field(default=False)
    json_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class MangaMetadata(ApprovedData, table=True):
    id: int = Field(primary_key=True)
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    nsfw: bool = Field(default=False)
    json_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))


data_engine = create_engine(sqlite_db_uri, echo=settings.SQL_ECHO)


def init_db() -> None:
    logger.info("Creating tables...")
    SQLModel.metadata.create_all(data_engine)


def get_db() -> Iterator[Session]:
    with Session(data_engine) as session:
        yield session


def add_or_update(
    *,
    summary: Summary,
    approved_status: Status,
    old_status: Optional[Status],
    in_db: Set[int],
    added_dt: Optional[datetime] = None,
) -> None:
    uu = urlparse(summary.url)
    assert uu.path.startswith("/v2")
    is_anime = uu.path.startswith("/v2/anime")
    entry_type = "anime" if is_anime else "manga"
    url_id = uu.path.split("/")[3]
    use_model = AnimeMetadata if is_anime else MangaMetadata

    jdata = dict(summary.metadata)
    if "error" in jdata:
        logger.debug(f"skipping http error in {entry_type} {url_id}: {jdata['error']}")
        return

    if "id" not in jdata:
        breakpoint()
    aid = int(jdata.pop("id"))
    title = jdata.pop("title")
    start_date = parse_date_safe(jdata.pop("start_date", None))
    end_date = parse_date_safe(jdata.pop("end_date", None))
    nsfw = jdata.pop("nsfw") != "white"

    if aid in in_db:
        # update the entry if the status has changed
        if approved_status != old_status or old_status is None:
            logger.info(f"updating data for {entry_type} {aid} (status changed)")
            # update the status to deleted
            stmt = (
                update(use_model)
                .where(use_model.id == aid)
                .values(
                    approved_status=approved_status,
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    json_data=jdata,
                    nsfw=nsfw,
                )
            )
            with Session(data_engine) as session:
                session.execute(stmt)
                session.commit()

    else:

        logger.info(f"adding {entry_type} {aid} to db")
        # add the entry
        with Session(data_engine) as sess:
            sess.add(
                use_model(
                    approved_status=approved_status,
                    approved_at=added_dt,
                    id=aid,
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    json_data=jdata,
                    nsfw=nsfw,
                )
            )
            sess.commit()


async def update_database() -> None:
    logger.info("Updating database...")
    with Session(data_engine) as sess:
        in_db: Dict[str, Any] = {
            "anime_tup": set(
                sess.query(AnimeMetadata.id, AnimeMetadata.approved_status)
            ),
            "manga_tup": set(
                sess.query(MangaMetadata.id, MangaMetadata.approved_status)
            ),
        }
    in_db["anime"] = set(i for i, _ in in_db["anime_tup"])
    in_db["manga"] = set(i for i, _ in in_db["manga_tup"])

    in_db["anime_status"] = {i: s for i, s in in_db["anime_tup"]}
    in_db["manga_status"] = {i: s for i, s in in_db["manga_tup"]}

    approved = approved_ids()
    logger.info("db: reading from linear history...")
    for hs in read_linear_history():
        dt = datetime.fromisoformat(hs["dt"]).replace(tzinfo=timezone.utc)
        approved_use: Set[int] = getattr(approved, hs["e_type"])

        # if its in the linear history, it was approved at one point
        # but it may not be anymore
        current_id_status = (
            Status.APPROVED if hs["entry_id"] in approved_use else Status.DELETED
        )

        add_or_update(
            summary=request_metadata(hs["entry_id"], hs["e_type"]),
            approved_status=current_id_status,
            old_status=in_db[f"{hs['e_type']}_status"].get(hs["entry_id"]),
            in_db=in_db[hs["e_type"]],
            added_dt=dt,
        )

    unapproved = unapproved_ids()
    logger.info("db: updating from unapproved history...")
    for aid in unapproved.anime:
        add_or_update(
            summary=request_metadata(aid, "anime"),
            old_status=in_db["anime_status"].get(aid),
            approved_status=Status.UNAPPROVED,
            in_db=in_db["anime"],
        )

    logger.info("db: updating from unapproved history...")
    for mid in unapproved.manga:
        add_or_update(
            summary=request_metadata(mid, "manga"),
            old_status=in_db["manga_status"].get(mid),
            approved_status=Status.UNAPPROVED,
            in_db=in_db["manga"],
        )
