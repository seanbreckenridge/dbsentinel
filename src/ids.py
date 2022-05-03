import time
from pathlib import Path
from functools import lru_cache
from typing import NamedTuple, Set, List, Any

import requests
import orjson

from src.paths import mal_id_cache_dir, unapproved_anime_path, unapproved_manga_path
from src.log import logger


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

SANITY_CHECK_AMOUNT = 10


def _request_unapproved(url) -> List[Any]:
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


REREQUEST_TIME = 60 * 10


@lru_cache(maxsize=2)
def _read_unapproved(path: Path, mtime: int) -> List[Any]:
    """
    Reads the unapproved anime/manga from the cache file,
    or from memory if the mtime hasnt changed
    """
    logger.debug(f"Caching new unapproved path {path} with updated {mtime} in memory")
    data = orjson.loads(path.read_text())
    assert isinstance(data, list), f"unapproved data is not a list: {data}"
    return data


def _update_unapproved(etype: str, cache_filepath: Path) -> List[Any]:
    """
    manages requesting/updating the cachefiles for anime/manga

    if the data hasnt changed, this will return the memcached data
    using the path/mtime as a key in the lru_cache above
    """
    url = UNAPPROVED_API_BASE + etype
    data: List[Any] = []
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
    # either the data hasnt changed (hasnt been 10 minutes, or the request failed and we should fallback)
    if data == []:
        data = _read_unapproved(cache_filepath, int(cache_filepath.stat().st_mtime))
        write_data = False
    assert (
        len(data) > SANITY_CHECK_AMOUNT
    ), f"sanity check failed, not enough unapproved entries {data}"
    if write_data:
        cache_filepath.write_bytes(orjson.dumps(data))
    else:
        logger.debug("Skipped writing unapproved data, request failed or no new data")
    return data


def unapproved_ids() -> Unapproved:
    anime = _update_unapproved("anime", unapproved_anime_path)
    manga = _update_unapproved("manga", unapproved_manga_path)
    return Unapproved(
        anime_info=[Entry(**a) for a in anime], manga_info=[Entry(**m) for m in manga]
    )
