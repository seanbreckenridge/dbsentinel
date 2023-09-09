import time
from pathlib import Path
from functools import lru_cache
from typing import NamedTuple, Set, List, Any
from datetime import datetime

import requests
import orjson
import backoff
from more_itertools import chunked
from malexport.exporter.mal_list import BASE_URL

from mal_id.paths import mal_id_cache_dir, unapproved_anime_path, unapproved_manga_path
from mal_id.log import logger
from mal_id.common import backoff_handler
from mal_id.parse_xml import parse_user_ids


class Approved(NamedTuple):
    anime: Set[int]
    manga: Set[int]


def approved_ids() -> Approved:
    anime_file = mal_id_cache_dir / "cache" / "anime_cache.json"
    manga_file = mal_id_cache_dir / "cache" / "manga_cache.json"
    anime = orjson.loads(anime_file.read_text())
    manga = orjson.loads(manga_file.read_text())
    return Approved(
        anime=set(anime["sfw"] + anime["nsfw"]),
        manga=set(manga["sfw"] + manga["nsfw"]),
    )


class Entry(NamedTuple):
    id: int
    name: str
    nsfw: bool
    type: str


class Unapproved(NamedTuple):
    anime_info: List[Entry]
    manga_info: List[Entry]

    @property
    def anime(self) -> Set[int]:
        return {info.id for info in self.anime_info}

    @property
    def manga(self) -> Set[int]:
        return {info.id for info in self.manga_info}


UNAPPROVED_API_BASE = "https://sean.fish/mal_unapproved/api/"
# UNAPPROVED_API_BASE = "http://localhost:4001/mal_unapproved/api/"

SANITY_CHECK_AMOUNT = 10


def _request_unapproved(url: str) -> List[Any]:
    logger.info("Requesting unapproved: {}".format(url))
    req = requests.get(url)
    req.raise_for_status()
    data: List[Any] = req.json()
    if len(data) < SANITY_CHECK_AMOUNT:
        raise RuntimeError(
            "Not enough unapproved entries -- server may be starting/down"
        )
    else:
        return data


REREQUEST_TIME = 60 * 5


@lru_cache(maxsize=2)
def _read_unapproved(path: Path, mtime: int) -> List[Any]:
    """
    Reads the unapproved anime/manga from the cache file,
    or from memory if the mtime hasnt changed
    """
    logger.debug(
        f"Caching new unapproved path {path} with updated at {datetime.fromtimestamp(mtime)} in memory"
    )
    data = orjson.loads(path.read_text())
    assert isinstance(data, list), f"unapproved data is not a list: {data}"
    return data


def _update_unapproved(
    etype: str, cache_filepath: Path, skip_request: bool
) -> List[Any]:
    """
    manages requesting/updating the cachefiles for anime/manga

    if the data hasnt changed, this will return the memcached data
    using the path/mtime as a key in the lru_cache above
    """
    data: List[Any] = []
    if skip_request:
        data = []
        write_data = False
    else:
        url = UNAPPROVED_API_BASE + etype
        data = []
        write_data = True  # dont want to overwrite/change mtime if theres no new data
        if not cache_filepath.exists():
            data = _request_unapproved(url)
        else:
            if cache_filepath.stat().st_mtime < (time.time() - REREQUEST_TIME):
                try:
                    logger.debug("Unapproved expired: {}".format(etype))
                    data = _request_unapproved(url)
                except (RuntimeError, requests.exceptions.RequestException) as e:
                    logger.exception(str(e), exc_info=e)
                    write_data = False
    # either the data hasnt changed (hasnt been 10 minutes, or the request failed and we should fallback to local file)
    if len(data) == 0:
        data = _read_unapproved(cache_filepath, int(cache_filepath.stat().st_mtime))
        write_data = False
    assert (
        len(data) > SANITY_CHECK_AMOUNT
    ), f"sanity check failed, not enough unapproved entries {data}"
    if write_data:
        cache_filepath.write_bytes(orjson.dumps(data))
    else:
        logger.debug(f"Skipped writing unapproved data, request failed or no new data for {etype}")
    return data


def unapproved_ids() -> Unapproved:
    anime = _update_unapproved("anime", unapproved_anime_path, skip_request=False)
    manga = _update_unapproved("manga", unapproved_manga_path, skip_request=False)
    return Unapproved(
        anime_info=[Entry(**a) for a in anime], manga_info=[Entry(**m) for m in manga]
    )


@backoff.on_exception(
    lambda: backoff.constant(5),
    requests.exceptions.RequestException,
    max_tries=3,
    on_backoff=backoff_handler,
)
def user_recently_updated(list_type: str, username: str, offset: int) -> Set[int]:
    time.sleep(5)
    assert list_type in {"anime", "manga"}
    url = BASE_URL.format(list_type=list_type, username=username, offset=offset)
    req = requests.get(url)
    if req.status_code in [400, 403]:
        if (
            "Content-Type" in req.headers
            and "application/json" in req.headers["Content-Type"]
        ):
            logger.warning(req.json())
        else:
            logger.warning(req.text)
        raise RuntimeError(
            f"Auth/Permission error retrieving {req.url}, probably a permission error; the user has restricted access to their list"
        )
    data = req.json()
    key = "anime_id" if list_type == "anime" else "manga_id"
    return set([int(entry[key]) for entry in data])


def _estimate_page(missing_id: int, sorted_ids: list[int]) -> int:
    """
    Estimate the page number of a missing (entry which was just approved) entry
    """
    assert missing_id > 1
    for page, chunk in enumerate(chunked(sorted_ids, 50), 1):
        # if the last page on this ID is smaller than the missing one, then we've passed where this would be
        if chunk[-1] < missing_id:
            return page
    # check all pages?
    # return len(sorted_ids) // 50
    raise RuntimeError(f"Could not find page for {missing_id}")


def estimate_using_user_recent(list_type: str, username: str) -> int:
    """
    Estimate the page number of a missing (entry which was just approved) entry
    and choose the max page number

    this requests a recent user's list, and uses checks if there are any
    ids in that list which arent in the approved cache
    """
    assert list_type in {"anime", "manga"}
    logger.info(f"Estimating {list_type}list using {username}")
    appr = approved_ids()
    recently_updated_ids = user_recently_updated(
        list_type=list_type, username=username, offset=0
    )
    ids = appr.anime if list_type == "anime" else appr.manga
    sorted_approved = list(sorted(ids, reverse=True))
    missing_approved = []
    for aid in recently_updated_ids:
        if aid not in ids:
            missing_approved.append(aid)
    estimate_pages = [_estimate_page(aid, sorted_approved) for aid in missing_approved]
    max_page: int
    if len(estimate_pages) == 0:
        max_page = 0
    else:
        max_page = max(estimate_pages) + 1
    logger.info(f"Estimated {max_page} {list_type} pages for {username}")
    return max_page


def estimate_all_users_max(
    user_names: List[str],
    check_type: str = "anime",
) -> int:
    max_pages = [estimate_using_user_recent(check_type, u) for u in user_names]
    return max(max_pages)


def estimate_deleted_entry(animelist_xml: Path) -> int:
    from mal_id.metadata_cache import mal_api_session

    assert animelist_xml.exists()

    try:
        my_user_ids = parse_user_ids(animelist_xml)
    except Exception as e:
        logger.exception(str(e), exc_info=e)
        return 0

    anime_ids = approved_ids().anime
    deleted_ids: Set[int] = anime_ids - my_user_ids

    if len(deleted_ids) == 0:
        return 0

    sess = mal_api_session()
    sorted_ids = sorted(anime_ids, reverse=True)

    for mid in sorted(deleted_ids):
        resp = sess.session.get(f"https://api.myanimelist.net/v2/anime/{mid}")
        time.sleep(1)
        if resp.status_code == 401:
            sess.refresh_token()
            return estimate_deleted_entry(animelist_xml)
        elif resp.status_code == 404:
            return _estimate_page(mid, sorted_ids)

    return 0
