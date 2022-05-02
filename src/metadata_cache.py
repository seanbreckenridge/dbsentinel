import os
import time
import logging
from typing import Any
from functools import cache
from pathlib import Path
from datetime import datetime

import click
import backoff
import requests

from malexport.exporter.mal_session import MalSession
from malexport.exporter.account import Account
from url_cache.core import URLCache, Summary

from src.paths import metadatacache_dir


def _get_img(data: dict) -> str | None:
    if img := data.get("medium"):
        return img
    if img := data.get("large"):
        return img
    return None


@backoff.on_exception(
    lambda: backoff.constant(3),
    requests.exceptions.RequestException,
    max_tries=3,
    on_backoff=lambda _: mal_api_session().refresh_token(),
)
def api_request(session: MalSession, url: str) -> Any:
    time.sleep(1)
    resp: requests.Response = session.session.get(url)
    if resp.status_code >= 400 and resp.status_code != 404:
        click.echo(f"Error {resp.status_code}: {resp.text}", err=True)
        time.sleep(60)
        return api_request(session, url)
    resp.raise_for_status()
    return resp.json()


@cache
def mal_api_session() -> MalSession:
    assert "MAL_USERNAME" in os.environ
    acc = Account.from_username(os.environ["MAL_USERNAME"])
    acc.mal_api_authenticate()
    assert acc.mal_session is not None
    return acc.mal_session


class MetadataCache(URLCache):

    BASE_URL = "https://api.myanimelist.net/v2/{etype}/{mal_id}?nsfw=true&fields=id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,created_at,updated_at,media_type,status,genres,my_list_status,num_episodes,start_season,broadcast,source,average_episode_duration,rating,pictures,background,related_anime,related_manga,recommendations,studios,statistics"

    def __init__(self, cache_dir: Path = metadatacache_dir) -> None:
        self.mal_session = mal_api_session()
        super().__init__(cache_dir=cache_dir, loglevel=logging.INFO)

    def request_data(self, url: str) -> Summary:
        uurl = self.preprocess_url(url)
        self.logger.info(f"requesting {uurl}")
        try:
            json_data = api_request(self.mal_session, uurl)
        except requests.exceptions.RequestException as ex:
            self.logger.exception(f"error requesting {uurl}", exc_info=ex)
            self.logger.warning("Couldn't cache info, assuming this a deleted entry?")
            return Summary(url=uurl, data={}, metadata={}, timestamp=datetime.now())
        return Summary(url=uurl, data={}, metadata=json_data, timestamp=datetime.now())

    def refresh_data(self, url: str) -> Summary:
        uurl = self.preprocess_url(url)
        summary = self.request_data(uurl)
        self.summary_cache.put(uurl, summary)
        return summary
