import os
import time
import logging
from typing import Any
from functools import cache
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock

import click
import requests

from malexport.exporter.mal_session import MalSession
from malexport.exporter.account import Account
from url_cache.core import URLCache
from url_cache.model import Summary

from mal_id.paths import metadatacache_dir
from mal_id.log import logger


class MALIsDownError(Exception):
    pass


MAL_API_LOCK = Lock()


def api_request(session: MalSession, url: str, recursed_times: int = 0) -> Any:
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

    if resp.status_code == 504:
        logger.warning(resp.text)
        if recursed_times >= 1:
            raise MALIsDownError("MAL returned 504 for entry, skipping for now")
        else:
            logger.warning(f"{url} recieved a 504, waiting and retrying once")
            time.sleep(5)
            return api_request(session, url, recursed_times + 1)

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
        super().__init__(cache_dir=cache_dir, loglevel=loglevel)

    def request_data(self, url: str, preprocess_url: bool = True) -> Summary:
        mal_id = int(url.split("/")[-1])
        media_type = url.split("/")[-2]
        assert media_type in ("anime", "manga")

        # this is the URL we use as they key, but not the one we cache
        myanimelist_url = url
        del url  # to be safe

        # this is the actual URL we want to request
        if media_type == "anime":
            api_url = self.BASE_ANIME_URL.format(mal_id) + "&" + self.ANIME_FIELDS
        else:
            api_url = self.BASE_MANGA_URL.format(mal_id) + "&" + self.MANGA_FIELDS

        api_url = self.preprocess_url(api_url) if preprocess_url else api_url

        logger.info(f"requesting {api_url}")
        try:
            # TODO: remove, Ive removed backoff from this code
            if "skip_retry" in self.options and self.options["skip_retry"] is True:
                json_data = api_request(self.mal_session, api_url)
            else:
                json_data = api_request(self.mal_session, api_url)
            # succeeded, return the data
            return Summary(
                url=myanimelist_url,
                data={},
                metadata=json_data,
                timestamp=datetime.now(),
            )
        except requests.exceptions.RequestException as ex:
            logger.exception(f"error requesting {api_url}", exc_info=ex)
            logger.warning(ex.response.text)
            logger.warning(
                "Couldn't cache info, could be deleted or failed to cache because entry data is broken/unapproved causing the MAL API to fail"
            )
            # TODO: this needs more testing to make sure we never overwrite good data
            # prevent a broken entry from removing old, valid data
            #
            # If it has valid but failed now, we should just keep the old valid data
            if self.summary_cache.has(myanimelist_url):
                logger.warning("using existing cached data for this entry")
                sc = self.summary_cache.get(myanimelist_url)
                assert sc is not None
                logger.info("Updating timestamp to prevent re-requesting this entry")
                # check if this has a few keys, i.e. (this isn't {"error": 404})
                if "error" in sc.metadata:
                    # if we had cached an error, then just return the error
                    # TODO: should we update the timestamp here? i dont think it hurts to, as this
                    # is just an error where we have no data. it just prevents possible re-requests
                    # of the same error in the future
                    sc.timestamp = datetime.now()
                    return sc
                else:
                    # we failed to get new data, but have old data
                    # so, just return the old data
                    assert "error" not in sc.metadata and MetadataCache.has_basic_data(
                        sc
                    ), f"{sc.metadata} does not have data"
                    # reusing old data is fine, but we should update the timestamp so
                    # we dont try to refresh it again for a while
                    sc.timestamp = datetime.now()
                    return sc
            else:
                # there is no existing data, and we failed to get new data,
                # so save an error to the cache
                # sanity check to make sure were not overwriting good data
                assert not self.summary_cache.has(myanimelist_url)
                logger.warning(
                    "no existing cached data for this entry, saving error to cache"
                )
                # this just doesn't exist (deleted a long time ago etc.?)
                # no way to get data for this
                return Summary(
                    url=myanimelist_url,
                    data={},
                    metadata={"error": ex.response.status_code},
                    timestamp=datetime.now(),
                )
        except MALIsDownError:
            logger.error(
                "MAL is down, skipping this entry for now. Will try again later."
            )
            return Summary(
                url=myanimelist_url,
                data={},
                metadata={"error": 504},
                timestamp=datetime.now(),
            )

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
    def has_broken_data(summary: Summary) -> bool:
        if "error" in summary.metadata and summary.metadata["error"] in {
            429,
            504,
        }:  # 429 probably has never happened
            return True

        if "currently under maintenance" in summary.metadata.get("message", "").lower():
            return True
        if summary.metadata.get("id") in {-1, 0}:
            return True
        # this is a sort of broken response that MAL returns sometimes when its down
        # {'id': -1, 'title': 'Title', 'num_chapters': 0, 'status': 'currently_publishing', 'media_type': 'manga'}
        if (
            set(summary.metadata.keys()).issubset(
                {"id", "title", "num_chapters", "status", "num_episodes", "media_type"}
            )
            and (
                summary.metadata.get("num_episodes") == 0
                or summary.metadata.get("num_chapters") == 0
            )
            and summary.metadata.get("title", "").lower()
            in {"title", "", "blocked.", "blocked"}
        ):
            return True
        return False

    @staticmethod
    def has_basic_data(summary: Summary) -> bool:
        if "error" in summary.metadata:
            return False
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
    # use this as the key for the cache
    url_key = "https://myanimelist.net/{}/{}".format(entry_type, id_)
    # if this had failed previously, try again
    #
    # this may never actually be the case, but just want to make sure if we
    # add some refresh mechanism that that does not happen...
    if rerequest_failed:
        sdata = mcache.get(url_key)
        if MetadataCache.is_404(sdata):
            logger.info("re-requesting failed entry: {}".format(sdata.metadata))
            return mcache.refresh_data(url_key)
    elif force_rerequest:
        logger.info("re-requesting entry")
        try:
            mcache.options["skip_retry"] = True
            dat = mcache.refresh_data(url_key)
        finally:
            mcache.options["skip_retry"] = False
        return dat

    # if something has truly broken data (like, 504s from when MAL was down, or during maintenance periods), re-request it
    data = mcache.get(url_key)
    # been_more_than_a_week
    if MetadataCache.has_broken_data(data):
        assert data.timestamp is not None
        time_since_last_request = timedelta(
            seconds=time.time() - data.timestamp.timestamp()
        )
        if time_since_last_request.days > 3:
            logger.info(f"Previously saved broken {data=}, retrying...")
            return mcache.refresh_data(url_key)
        else:
            logger.info(
                f"Previously saved broken {data=}, waiting {timedelta(days=7) - time_since_last_request} days before re-requesting"
            )
    return data


def has_metadata(
    id_: int,
    entry_type: str,
) -> bool:
    assert entry_type in {"anime", "manga"}
    # use this as the key for the cache
    url_key = "https://myanimelist.net/{}/{}".format(entry_type, id_)
    return metadata_cache().summary_cache.has(url_key)
