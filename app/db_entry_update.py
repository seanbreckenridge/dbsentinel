from typing import Optional, Set, Dict, Any
from datetime import datetime, timezone
from asyncio import sleep

from urllib.parse import urlparse
from malexport.parse.common import parse_date_safe
from sqlalchemy import update, select
from sqlmodel import Session
from url_cache.core import Summary

from src.metadata_cache import request_metadata
from src.linear_history import read_linear_history
from src.ids import approved_ids, unapproved_ids
from src.paths import metadatacache_dir
from src.log import logger

from app.db import Status, AnimeMetadata, MangaMetadata, data_engine


def api_url_to_parts(url: str) -> tuple[str, int]:
    uu = urlparse(url)
    assert uu.path.startswith("/v2")
    is_anime = uu.path.startswith("/v2/anime")
    entry_type = "anime" if is_anime else "manga"
    url_id = uu.path.split("/")[3]
    return entry_type, int(url_id)


def add_or_update(
    *,
    summary: Summary,
    current_approved_status: Status | None = None,
    old_status: Optional[Status] = None,
    in_db: Optional[Set[int]] = None,
    added_dt: Optional[datetime] = None,
    force_update: bool = False,
) -> None:
    entry_type, url_id = api_url_to_parts(summary.url)
    assert entry_type in ("anime", "manga")
    use_model = AnimeMetadata if entry_type == "anime" else MangaMetadata

    jdata = dict(summary.metadata)
    if "error" in jdata:
        logger.debug(f"skipping http error in {entry_type} {url_id}: {jdata['error']}")
        return

    # pop data from the json that get stored in the db
    aid = int(jdata.pop("id"))
    title = jdata.pop("title")
    start_date = parse_date_safe(jdata.pop("start_date", None))
    end_date = parse_date_safe(jdata.pop("end_date", None))

    # try to figure out if this is sfw/nsfw
    sfw: Optional[bool] = None
    if rating := jdata.get("rating"):
        if rating == "rx":
            sfw = False
    elif nsfw_val := jdata.get("nsfw"):
        if sfw is None and nsfw_val == "white":
            sfw = True
    elif genres := jdata.get("genres"):
        if sfw is None and "Hentai" in (g["name"] for g in genres):
            sfw = False

    nsfw = not sfw if sfw is not None else None

    # figure out if entry is the in db
    # if force rerequesting, dont have access to in_db/statuses
    entry_in_db = False
    if in_db is not None:
        entry_in_db = aid in in_db
    elif force_update:
        with Session(data_engine) as sess:
            entry_req = list(sess.exec(select(use_model).where(use_model.id == aid)))
            entry_in_db = len(entry_req) > 0

    if entry_in_db:
        # update the entry if the status has changed or if this didnt exist in the db
        if force_update or (
            (
                current_approved_status is not None
                and current_approved_status != old_status
            )
            or old_status is None
        ):
            logger.info(f"updating data for {entry_type} {aid} (status changed)")
            kwargs = {}
            if current_approved_status is not None:
                kwargs["approved_status"] = current_approved_status
            # update the status to deleted
            stmt = (
                update(use_model)
                .where(use_model.id == aid)
                .values(
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    json_data=jdata,
                    updated_at=datetime.utcnow(),
                    nsfw=nsfw,
                    **kwargs,
                )
            )
            with Session(data_engine) as sess:
                sess.execute(stmt)
                sess.commit()
    else:
        if current_approved_status is None:
            logger.warning(
                f"trying to add {entry_type} {aid} with status as None! skipping..."
            )
            return
        logger.info(f"adding {entry_type} {aid} to db")
        # add the entry
        with Session(data_engine) as sess:
            sess.add(
                use_model(
                    approved_status=current_approved_status,
                    approved_at=added_dt,
                    id=aid,
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    updated_at=datetime.utcnow(),
                    json_data=jdata,
                    nsfw=nsfw,
                )
            )
            sess.commit()


async def status_map() -> Dict[str, Any]:
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

    return in_db


async def update_database() -> None:
    logger.info("Updating database...")

    known: Set[str] = set()
    in_db = await status_map()

    approved = approved_ids()
    logger.info("db: reading from linear history...")
    for i, hs in enumerate(read_linear_history()):
        # be nice to other tasks
        if i % 10 == 0:
            await sleep(0)
        dt = datetime.fromisoformat(hs["dt"]).replace(tzinfo=timezone.utc)
        approved_use: Set[int] = getattr(approved, hs["e_type"])

        # if its in the linear history, it was approved at one point
        # but it may not be anymore
        current_id_status = (
            Status.APPROVED if hs["entry_id"] in approved_use else Status.DELETED
        )

        add_or_update(
            summary=request_metadata(hs["entry_id"], hs["e_type"]),
            current_approved_status=current_id_status,
            old_status=in_db[f"{hs['e_type']}_status"].get(hs["entry_id"]),
            in_db=in_db[hs["e_type"]],
            added_dt=dt,
        )
        known.add(f"{hs['e_type']}_{hs['entry_id']}")

    unapproved = unapproved_ids()
    logger.info("db: updating from unapproved anime history...")
    for i, aid in enumerate(unapproved.anime):
        if i % 10 == 0:
            await sleep(0)
        add_or_update(
            summary=request_metadata(aid, "anime"),
            old_status=in_db["anime_status"].get(aid),
            current_approved_status=Status.UNAPPROVED,
            in_db=in_db["anime"],
        )
        known.add(f"anime_{aid}")

    logger.info("db: updating from unapproved manga history...")
    for i, mid in enumerate(unapproved.manga):
        if i % 10 == 0:
            await sleep(0)
        add_or_update(
            summary=request_metadata(mid, "manga"),
            old_status=in_db["manga_status"].get(mid),
            current_approved_status=Status.UNAPPROVED,
            in_db=in_db["manga"],
        )
        known.add(f"manga_{mid}")

    logger.info("db: checking for deleted entries...")
    # check if any other items exist that arent in the db already
    # those were denied or deleted (long time ago)
    all_keys = [p.absolute() for p in metadatacache_dir.rglob("*/key")]
    all_urls = set(p.read_text() for p in all_keys)
    for i, (entry_type, entry_id) in enumerate(map(api_url_to_parts, all_urls)):
        if i % 10 == 0:
            await sleep(0)
        if f"{entry_type}_{entry_id}" not in known:
            # already inserted into the db
            if entry_id in in_db[entry_type]:
                continue
            add_or_update(
                summary=request_metadata(entry_id, entry_type),
                current_approved_status=Status.DENIED,
            )


async def refresh_entry(*, entry_id: int, entry_type: str) -> None:
    summary = request_metadata(entry_id, entry_type, force_rerequest=True)
    await sleep(0)
    logger.info(f"db: refreshed data {summary.metadata}")
    add_or_update(
        summary=summary,
        force_update=True,
    )
