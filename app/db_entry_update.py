from typing import Optional, Set, Dict, Any, Tuple, List, Mapping, NamedTuple
from datetime import datetime, date, timedelta
from asyncio import sleep
from collections import defaultdict
from pathlib import Path

from urllib.parse import urlparse
from malexport.parse.common import parse_date_safe
from sqlalchemy import update
from sqlmodel import Session
from sqlmodel.sql.expression import select
from url_cache.core import Summary

from mal_id.metadata_cache import request_metadata
from mal_id.linear_history import iter_linear_history, Entry
from mal_id.ids import approved_ids, unapproved_ids
from mal_id.paths import metadatacache_dir
from mal_id.log import logger
from mal_id.common import to_utc

from app.db import (
    Status,
    AnimeMetadata,
    MangaMetadata,
    data_engine,
    ProxiedImage,
    EntryType,
)
from app.image_proxy import proxy_image


def api_url_to_parts(url: str) -> tuple[str, int]:
    uu = urlparse(url)
    assert uu.path.startswith("/v2")
    is_anime = uu.path.startswith("/v2/anime")
    entry_type = "anime" if is_anime else "manga"
    url_id = uu.path.split("/")[3]
    return entry_type, int(url_id)


def mal_url_to_parts(url: str) -> tuple[str, int]:
    uu = urlparse(url)
    assert uu.path.startswith("/anime") or uu.path.startswith(
        "/manga"
    ), f"broken url {url}"
    is_anime = uu.path.startswith("/anime")
    entry_type = "anime" if is_anime else "manga"
    url_id = uu.path.split("/")[2]
    return entry_type, int(url_id)


def test_api_url_to_parts() -> None:
    assert api_url_to_parts(
        "https://api.myanimelist.net/v2/manga/113372?nsfw=true&fields=id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,created_at,updated_at,media_type,status,genres,num_volumes,num_chapters,authors{first_name,last_name},pictures,background,related_anime,related_manga,recommendations,serialization{name}"
    ) == ("manga", 113372)

    assert api_url_to_parts(
        "https://api.myanimelist.net/v2/anime/48420?nsfw=true&fields=id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,created_at,updated_at,media_type,status,genres,num_episodes,start_season,broadcast,source,average_episode_duration,rating,pictures,background,related_anime,related_manga,recommendations,studios,statistics"
    ) == ("anime", 48420)


def test_mal_url_to_parts() -> None:
    assert mal_url_to_parts("https://myanimelist.net/anime/48420/86") == (
        "anime",
        48420,
    )

    assert mal_url_to_parts("https://myanimelist.net/manga/113372/86") == (
        "manga",
        113372,
    )


class ImageData(NamedTuple):
    mal_url: str
    proxied_url: str


# ???
# who even knows what gray nsfw means??
# some that have hentai in manga are marked grey, others aren't?
def is_nsfw(jdata: Dict[str, Any]) -> Optional[bool]:
    if "rating" in jdata:
        return bool(jdata["rating"] == "rx")
    else:
        if "genres" in jdata:
            return bool("Hentai" in (g["name"] for g in jdata["genres"]))
    return None


def _get_img_url(data: dict) -> str | None:
    if img := data.get("medium"):
        assert isinstance(img, str)
        return img
    if img := data.get("large"):
        assert isinstance(img, str)
        return img
    return None


def summary_main_image(summary: Summary) -> str | None:
    if pictures := summary.metadata.get("main_picture"):
        if img := _get_img_url(pictures):
            return img
    return None


async def summary_proxy_image(summary: Summary) -> str | None:
    if main_image := summary_main_image(summary):
        return await proxy_image(main_image)
    return None


async def add_or_update(
    *,
    summary: Summary,
    current_approved_status: Status | None = None,
    old_status: Optional[Status] = None,
    in_db: Optional[Set[int]] = None,
    status_changed_at: Optional[datetime] = None,
    force_update: bool = False,
    mal_id_to_image: Optional[Dict[Tuple[EntryType, int], ImageData]] = None,
    refresh_images: bool = False,
    skip_images: bool = False,
) -> None:
    entry_type, url_id = mal_url_to_parts(summary.url)
    entry_enum = EntryType.from_str(entry_type)
    assert entry_type in ("anime", "manga")

    jdata = dict(summary.metadata)
    if "error" in jdata:
        logger.debug(f"skipping http error in {entry_type} {url_id}: {jdata['error']}")
        return

    if skip_images is False:
        img = await summary_proxy_image(summary)  # this is where the image is proxied
        await sleep(0)
        # may be that the summary is so old a new image has been added instead
        if img is None and refresh_images is True:
            summary = request_metadata(url_id, entry_type, force_rerequest=True)
            await sleep(0)
            img = await summary_proxy_image(summary)
            await sleep(0)
            if img is not None:
                logger.info(
                    f"db: {entry_type} {url_id} successfully refreshed image {img}"
                )

        # if force refreshing an entry, select the single image row from the db
        # mal_id_to_image is passed in a full update
        if mal_id_to_image is None:
            logger.debug(f"db: {entry_type} {url_id} fetching image row from db")
            with Session(data_engine) as sess:
                mal_id_to_image = {
                    (i.mal_entry_type, i.mal_id): ImageData(
                        mal_url=i.mal_url,
                        proxied_url=i.proxied_url,
                    )
                    for i in sess.exec(
                        select(ProxiedImage)
                        .where(ProxiedImage.mal_id == url_id)
                        .where(ProxiedImage.mal_entry_type == entry_enum)
                    ).all()
                }
            await sleep(0)

        assert mal_id_to_image is not None

        # if we have the local dict db and we have a proxied image
        if img is not None:
            mal_image_url = summary_main_image(summary)

            image_key = (entry_enum, url_id)

            if mal_image_url is not None:
                # if this isn't already in the database
                if image_key not in mal_id_to_image:
                    logger.info(f"db: adding proxied image for {entry_type} {url_id}")
                    with Session(data_engine) as sess:
                        sess.add(
                            ProxiedImage(
                                mal_entry_type=entry_enum,
                                mal_id=url_id,
                                mal_url=mal_image_url,
                                proxied_url=img,
                            )
                        )
                        sess.commit()
                    await sleep(0)
                else:
                    # if we have the image in the database and it is different
                    if (
                        mal_id_to_image[image_key].proxied_url != img
                        or mal_id_to_image[image_key].mal_url != mal_image_url
                    ):
                        logger.info(
                            f"db: mal or proxied image changed for {entry_type} {url_id}"
                        )
                        with Session(data_engine) as sess:
                            sess.exec(
                                update(ProxiedImage)  # type: ignore
                                .where(ProxiedImage.mal_entry_type == entry_enum)
                                .where(ProxiedImage.mal_id == url_id)
                                .values(mal_url=mal_image_url, proxied_url=img)
                            )
                            sess.commit()
                        await sleep(0)

                # we should also check if the main image has changed, and if so, update it

    use_model = AnimeMetadata if entry_type == "anime" else MangaMetadata

    # pop data from the json that get stored in the db
    aid = int(jdata.pop("id"))
    title = jdata.pop("title")
    media_type = jdata.pop("media_type", None)
    start_date = parse_date_safe(jdata.pop("start_date", None))
    end_date = parse_date_safe(jdata.pop("end_date", None))
    member_count = jdata.pop("num_list_users", None)
    average_episode_duration = jdata.pop("average_episode_duration", None)

    # try to figure out if this is sfw/nsfw
    nsfw = is_nsfw(jdata)

    # figure out if entry is the in db
    # if force rerequesting, dont have access to in_db/statuses
    entry_in_db = False
    if in_db is not None:
        entry_in_db = aid in in_db
    else:
        with Session(data_engine) as sess:
            entry_req = sess.exec(select(use_model).where(use_model.id == aid)).first()
            entry_in_db = entry_req is not None
            await sleep(0)

            # if we have the entry in the db, get the current status
            # 'denied' entries need this to function so were not writing all the time
            if old_status is None and entry_req is not None:
                old_status = entry_req.approved_status

    # if we have a current status, use it
    if old_status is None:
        with Session(data_engine) as sess:
            entry_req = sess.exec(select(use_model).where(use_model.id == aid)).first()
            if entry_req is not None:
                old_status = entry_req.approved_status
        await sleep(0)

    if entry_in_db:
        # update the entry if the status has changed or if this didn't exist in the db
        if force_update or (
            (
                current_approved_status is not None
                and current_approved_status != old_status
            )
            or old_status is None
        ):
            if force_update:
                logger.debug(f"db: {entry_type} {aid} force updating")
            else:
                logger.info(
                    f"updating data for {entry_type} {aid} (status changed from {old_status} to {current_approved_status})"
                )
            kwargs: Dict[str, Any] = {}
            if current_approved_status is not None:
                kwargs["approved_status"] = current_approved_status
            if status_changed_at is not None:
                kwargs["status_changed_at"] = status_changed_at
            # this updates all the metadata for the entry as its popped from the json
            # the status_changed_at/datetime is not dependent on code here, its read from the JSON linear history etc.
            stmt = (
                update(use_model)
                .where(use_model.id == aid)  # type: ignore[attr-defined]
                .values(
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    json_data=jdata,
                    media_type=media_type,
                    updated_at=summary.timestamp,
                    member_count=member_count,
                    average_episode_duration=average_episode_duration,
                    nsfw=nsfw,
                    **kwargs,
                )
            )
            with Session(data_engine) as sess:
                sess.exec(stmt)  # type: ignore[call-overload]
                sess.commit()
    else:
        if current_approved_status is None:
            logger.warning(
                f"trying to add {entry_type} {aid} with status as None! skipping..."
            )
            return
        if status_changed_at is None:
            logger.warning(
                f"trying to add {entry_type} {aid} with status_changed_at as None! skipping..."
            )
            return
        logger.info(f"adding {entry_type} {aid} to db")
        # add the entry
        with Session(data_engine) as sess:
            assert summary.timestamp is not None
            sess.add(
                use_model(
                    approved_status=current_approved_status,
                    status_changed_at=status_changed_at,
                    id=aid,
                    title=title,
                    start_date=start_date,
                    end_date=end_date,
                    media_type=media_type,
                    updated_at=summary.timestamp,
                    json_data=jdata,
                    member_count=member_count,
                    average_episode_duration=average_episode_duration,
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


def malid_to_image() -> Dict[Tuple[EntryType, int], ImageData]:
    with Session(data_engine) as sess:
        return {
            (i.mal_entry_type, i.mal_id): ImageData(
                mal_url=i.mal_url, proxied_url=i.proxied_url
            )
            for i in sess.exec(select(ProxiedImage)).all()
        }


def parse_datetime_from_dict(data: dict, key: str) -> Optional[datetime]:
    if key in data:
        try:
            return to_utc(datetime.fromisoformat(data[key]))
        except ValueError:
            return None
    return None


def unapproved_summary_datetime(summary: Summary) -> datetime:
    if dd := parse_datetime_from_dict(summary.metadata, "created_at"):
        return dd
    assert summary.timestamp is not None
    return summary.timestamp


def deleted_last_datetime(
    summary: Summary, dates: Optional[List[datetime]] = None
) -> datetime:
    if dates is None:
        dates = []
    if cd := parse_datetime_from_dict(summary.metadata, "created_at"):
        dates.append(cd)
    if dd := parse_datetime_from_dict(summary.metadata, "updated_at"):
        dates.append(dd)
    assert summary.timestamp is not None
    dates.append(summary.timestamp)
    return max(map(to_utc, dates))


async def update_database(
    refresh_images: bool = False,
    force_update_db: bool = False,
    skip_proxy_images: bool = False,
    # updates this many entries of data if the data is older than 'update_if_older_than'
    update_outdated_metadata: Optional[int] = None,
    update_if_older_than: timedelta = timedelta(days=182),  # 6 months
) -> None:
    if update_outdated_metadata is not None:
        assert update_outdated_metadata > 0
    now = datetime.now()

    #  make sure MAL API is up
    from mal_id.metadata_cache import check_mal

    if not check_mal():
        logger.warning("mal api is down, skipping db update")
        return

    logger.info("Updating database...")

    known: Set[str] = set()
    in_db = await status_map()
    mal_id_image_have = malid_to_image()

    expired_entries: int = 0

    approved = approved_ids()
    logger.info("db: reading from linear history...")

    # create a map from ID -> List[Entry]
    history_map: Mapping[Tuple[int, str], List[Entry]] = defaultdict(list)
    for ent in iter_linear_history():
        history_map[(ent.entry_id, ent.e_type)].append(ent)

    for (r_id, r_type), r_appearances in history_map.items():
        # sort by timestamp
        r_appearances.sort(key=lambda x: x.dt)

        assert r_type in ("anime", "manga")
        approved_use: Set[int] = approved.anime if r_type == "anime" else approved.manga

        # if its in the linear history, it was approved at one point
        # but it may not be anymore
        current_id_status = Status.APPROVED if r_id in approved_use else Status.DELETED

        old_status = in_db[f"{r_type}_status"].get(r_id)
        was_approved = False
        if current_id_status == Status.APPROVED and old_status == Status.UNAPPROVED:
            logger.info(
                f"updating {r_type} {r_id} to approved (was unapproved), rerequesting data"
            )
            was_approved = True

        smmry = request_metadata(r_id, r_type, force_rerequest=was_approved)

        if "error" in smmry.metadata:
            logger.debug(f"skipping http error in {r_type} {r_id}")
            continue

        # if we're trying to refresh a couple entries each time we update, do that
        force_db_update_for_this_entry = force_update_db
        if update_outdated_metadata is not None and update_outdated_metadata > 0:
            # check if its expired
            requested_at = smmry.timestamp
            assert requested_at is not None
            # update manga at a slower rate
            upd = (
                update_if_older_than
                if r_type == "anime"
                else timedelta(days=update_if_older_than.days * 2)
            )
            if now - requested_at > upd:
                logger.info(
                    f"Rerequesting expired data for {r_type} {r_id}, requesting {update_outdated_metadata} more..."
                )
                update_outdated_metadata -= 1
                force_db_update_for_this_entry = True
                # print old main image and whether its proxied or not
                old_main_image = summary_main_image(smmry)
                if old_main_image is None:
                    logger.info("old main image: None")
                else:
                    logger.info(f"old main image: {old_main_image}")
                smmry = request_metadata(r_id, r_type, force_rerequest=True)
        else:
            requested_at = smmry.timestamp
            assert requested_at is not None
            if now - requested_at > update_if_older_than:
                expired_entries += 1

        # figure out when this was approved/deleted
        status_changed_at = None
        if current_id_status == Status.APPROVED:
            entry_created_at = parse_datetime_from_dict(smmry.metadata, "created_at")
            # this was the date mal-id-cache metadata was created, so if its before that, use
            # the MAL API created_at field. otherwise, use when it appeared in our
            # cache, since otherwise the created_at is when the entry was submitted
            # by a user to MAL, not when it was approved
            if entry_created_at is not None and entry_created_at.date() < date(
                2022, 3, 15
            ):
                status_changed_at = entry_created_at
            else:
                # use the first value from git history
                status_changed_at = r_appearances[0].dt
        elif current_id_status == Status.DELETED:
            status_changed_at = deleted_last_datetime(
                smmry, dates=[r.dt for r in r_appearances if r.action is False]
            )

        assert (
            status_changed_at is not None
        ), f"no status changed at for {r_id} {r_type}"

        await add_or_update(
            summary=smmry,
            current_approved_status=current_id_status,
            old_status=old_status,
            in_db=in_db[r_type],
            status_changed_at=status_changed_at,
            refresh_images=refresh_images,
            force_update=force_db_update_for_this_entry,
            skip_images=skip_proxy_images,
            mal_id_to_image=mal_id_image_have,
        )
        ekey = r_appearances[0].key
        known.add(ekey)

    logger.info(f"db: {expired_entries} entries are currently expired")

    unapproved = unapproved_ids()
    logger.info("db: updating from unapproved anime history...")
    for aid in unapproved.anime:
        aid_key = f"anime_{aid}"
        if aid_key in known:
            logger.warning(f"skipping anime {aid} as it was already processed this run")
            continue
        smmry = request_metadata(aid, "anime")
        await add_or_update(
            summary=smmry,
            old_status=in_db["anime_status"].get(aid),
            current_approved_status=Status.UNAPPROVED,
            status_changed_at=unapproved_summary_datetime(smmry),
            in_db=in_db["anime"],
            refresh_images=refresh_images,
            force_update=force_update_db,
            skip_images=skip_proxy_images,
            mal_id_to_image=mal_id_image_have,
        )
        known.add(aid_key)

    logger.info("db: updating from unapproved manga history...")
    for mid in unapproved.manga:
        mid_key = f"manga_{mid}"
        if mid_key in known:
            logger.warning(f"skipping manga {mid} as it was already processed this run")
            continue
        smmry = request_metadata(mid, "manga")
        await add_or_update(
            summary=smmry,
            old_status=in_db["manga_status"].get(mid),
            current_approved_status=Status.UNAPPROVED,
            in_db=in_db["manga"],
            status_changed_at=unapproved_summary_datetime(smmry),
            refresh_images=refresh_images,
            force_update=force_update_db,
            skip_images=skip_proxy_images,
            mal_id_to_image=mal_id_image_have,
        )
        known.add(mid_key)

    logger.info("db: checking for deleted entries...")
    # check if any other items exist that aren't in the db already
    # those were denied or deleted (long time ago)
    all_urls = set()
    for keyfile in (Path(metadatacache_dir) / "data").rglob("*/key"):
        all_urls.add(keyfile.read_text().strip())
    for entry_type, entry_id in map(mal_url_to_parts, all_urls):
        key = f"{entry_type}_{entry_id}"
        if key in known:
            continue
        old_status = in_db[f"{entry_type}_status"].get(entry_id)
        smmry = request_metadata(entry_id, entry_type)
        await add_or_update(
            summary=smmry,
            in_db=in_db[entry_type],
            old_status=old_status,
            status_changed_at=deleted_last_datetime(smmry),
            current_approved_status=Status.DENIED,
            refresh_images=refresh_images,
            force_update=force_update_db,
            skip_images=skip_proxy_images,
            mal_id_to_image=mal_id_image_have,
        )
        known.add(key)

    logger.info("db: done with full update")


async def refresh_entry(*, entry_id: int, entry_type: str) -> None:
    summary = request_metadata(entry_id, entry_type, force_rerequest=True)
    await sleep(0)
    logger.info(f"db: refreshed data for {entry_type} {entry_id}")
    # just update the basic metadata
    # Note:
    # this doesn't updated current_approved_status or status_changed_at
    # that should be done by the full update
    await add_or_update(
        summary=summary,
        force_update=True,
    )
