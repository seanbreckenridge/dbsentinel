import os
import time
import logging
from typing import Any
from functools import cache
from pathlib import Path
from datetime import datetime
from threading import Lock

import click
import backoff
import requests

from malexport.exporter.mal_session import MalSession
from malexport.exporter.account import Account
from url_cache.core import URLCache, Summary

from mal_id.common import backoff_handler
from mal_id.paths import metadatacache_dir
from mal_id.log import logger


MAL_API_LOCK = Lock()


@backoff.on_exception(
    lambda: backoff.constant(5),
    requests.exceptions.RequestException,
    max_tries=3,
    on_backoff=backoff_handler,
)
def api_request(session: MalSession, url: str, recursed_times: int = 0) -> Any:
    return _api_request(session, url, recursed_times)


def _api_request(session: MalSession, url: str, recursed_times: int = 0) -> Any:
    with MAL_API_LOCK:
        time.sleep(1)
        resp: requests.Response = session.session.get(url)

    # sometimes 400 happens if the alternative titles are empty
    if resp.status_code == 400 and "alternative_titles," in url:
        if recursed_times > 2:
            resp.raise_for_status()
        logger.warning("trying to remove alternative titles and re-requesting")
        url = url.replace("alternative_titles,", "")
        return api_request(session, url, recursed_times + 1)

    # if token expired, refresh
    if resp.status_code == 401:
        logger.warning("token expired, refreshing")
        refresh_token()
        resp.raise_for_status()

    # if this is an unexpected API failure, and not an expected 404/429/400, wait for a while before retrying
    if resp.status_code == 429:
        logger.warning("API rate limit exceeded, waiting")
        time.sleep(60)
        resp.raise_for_status()

    # for any other error, backoff for a minute and then retry
    # if over 5 times, raise the error
    if (
        recursed_times < 5
        and resp.status_code >= 400
        and resp.status_code not in (404,)
    ):
        click.echo(f"Error {resp.status_code}: {resp.text}", err=True)
        time.sleep(60)
        return api_request(session, url, recursed_times + 1)

    # fallthrough raises error if none of the conditions above match
    resp.raise_for_status()

    # if we get here, we have a successful response
    return resp.json()


@cache
def mal_api_session() -> MalSession:
    assert "MAL_USERNAME" in os.environ
    acc = Account.from_username(os.environ["MAL_USERNAME"])
    acc.mal_api_authenticate()
    assert acc.mal_session is not None
    return acc.mal_session


def refresh_token() -> None:
    mal_api_session().refresh_token()


def check_mal() -> bool:
    try:
        logger.info("checking if MAL API is up...")
        resp = mal_api_session().session.get("https://api.myanimelist.net/v2/anime/1")
        if resp.status_code == 401:
            refresh_token()
            return check_mal()
        resp.raise_for_status()
        data = resp.json()
        assert data["id"] == 1
        assert data["title"] == "Cowboy Bebop"
        logger.info("MAL API is up")
        return True
    except requests.exceptions.RequestException as e:
        logger.warning("MAL API is down!", exc_info=e)
        return False


class MetadataCache(URLCache):
    BASE_ANIME_URL = "https://api.myanimelist.net/v2/anime/{}?nsfw=true"

    ANIME_FIELDS = "fields=id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,created_at,updated_at,media_type,status,genres,num_episodes,start_season,broadcast,source,average_episode_duration,rating,pictures,background,related_anime,related_manga,recommendations,studios,statistics"

    BASE_MANGA_URL = r"https://api.myanimelist.net/v2/manga/{}?nsfw=true"

    MANGA_FIELDS = "fields=id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,created_at,updated_at,media_type,status,genres,num_volumes,num_chapters,authors{first_name,last_name},pictures,background,related_anime,related_manga,recommendations,serialization{name}"

    def __init__(
        self, cache_dir: Path = metadatacache_dir, loglevel: int = logging.INFO
    ) -> None:
        self.mal_session = mal_api_session()
        # hmm -- this expires every ~9 years or so as a fallback for now
        # when stuff was actually expiring it looked like it was breaking/ovewriting the old
        # cache even though these were 404s (which was never meant to happen)
        #
        # made a backup of the database to somewhere local incase that actually did
        # malform some of the data in the metadata cache
        super().__init__(
            cache_dir=cache_dir, loglevel=loglevel, options={"expiry_duration": "520w"}
        )

    def request_data(self, url: str, preprocess_url: bool = True) -> Summary:
        #
        # this may never actually be the case, but just want to make sure if we
        # add some refresh mechanism that that does not happen...
        if preprocess_url:
            uurl = self.preprocess_url(url)
        else:
            uurl = url
        logger.info(f"requesting {uurl}")
        try:
            if "skip_retry" in self.options and self.options["skip_retry"] is True:
                json_data = _api_request(self.mal_session, uurl)
            else:
                json_data = api_request(self.mal_session, uurl)
        except requests.exceptions.RequestException as ex:
            logger.exception(f"error requesting {uurl}", exc_info=ex)
            logger.warning(ex.response.text)
            logger.warning(
                "Couldn't cache info, could be deleted or failed to cache because entry data is broken/unapproved causing the MAL API to fail"
            )
            # prevent a broken entry from removing old, valid data
            #
            # If it has valid but failed now, we should just keep the old valid data
            if self.summary_cache.has(uurl):
                logger.warning("using existing cached data for this entry")
                sc = self.summary_cache.get(uurl)
                assert sc is not None
                # check if this has a few keys, i.e. (this isnt {"error": 404})
                if len(sc.metadata.keys()) > 5:
                    return sc
            logger.warning(
                "no existing cached data for this entry, saving error to cache"
            )
            # this just doesnt exist (deleted a long time ago etc.?)
            # no way to get data for this
            return Summary(
                url=uurl,
                data={},
                metadata={"error": ex.response.status_code},
                timestamp=datetime.now(),
            )
        return Summary(url=uurl, data={}, metadata=json_data, timestamp=datetime.now())

    def refresh_data(self, url: str) -> Summary:
        uurl = self.preprocess_url(url)
        summary = self.request_data(uurl)
        self.summary_cache.put(uurl, summary)
        return summary

    @staticmethod
    def is_404(summary: Summary) -> bool:
        if "error" in summary.metadata:
            return bool(summary.metadata["error"] == 404)
        return False

    @staticmethod
    def has_data(summary: Summary) -> bool:
        return all(k in summary.metadata for k in ("title", "id"))


@cache
def metadata_cache() -> MetadataCache:
    return MetadataCache()


def request_metadata(
    id_: int,
    entry_type: str,
    /,
    *,
    rerequest_failed: bool = False,
    force_rerequest: bool = False,
    mcache: MetadataCache = metadata_cache(),
) -> Summary:
    assert entry_type in {"anime", "manga"}
    if entry_type == "anime":
        api_url = mcache.BASE_ANIME_URL.format(id_) + "&" + mcache.ANIME_FIELDS
    else:
        api_url = mcache.BASE_MANGA_URL.format(id_) + "&" + mcache.MANGA_FIELDS
    if rerequest_failed:
        sdata = mcache.get(api_url)
        # if theres no data and this isnt a 404, retry
        if not MetadataCache.has_data(sdata) and not MetadataCache.is_404(sdata):
            logger.info("re-requesting failed entry: {}".format(sdata.metadata))
            return mcache.refresh_data(api_url)
    elif force_rerequest:
        logger.info("re-requesting entry")
        try:
            mcache.options["skip_retry"] = True
            dat = mcache.refresh_data(api_url)
        finally:
            mcache.options["skip_retry"] = False
        return dat
    return mcache.get(api_url)
