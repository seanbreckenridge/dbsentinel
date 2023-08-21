import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from functools import cache

import requests

from mal_id.log import logger
from mal_id.paths import anilist_cache as cpath
from url_cache.core import URLCache, Summary

GRAPHQL_URL = "https://graphql.anilist.co"


class AnilistCache(URLCache):
    def __init__(self, cache_dir: Path = cpath, loglevel: int = logging.INFO) -> None:
        super().__init__(
            cache_dir=cache_dir, loglevel=loglevel, options={"expiry_duration": "25w"}
        )

    def preprocess_url(self, url: str) -> str:
        uurl = url.strip("/")
        return super().preprocess_url(uurl)

    @staticmethod
    def fetch_anilist_data(mal_id: int, media_type: str) -> Optional[Dict[str, Any]]:
        query = """query($id: Int, $type: MediaType){Media(idMal: $id, type: $type){
            id
            idMal
            type
        }}"""
        mtype = media_type.upper()
        assert mtype in ("ANIME", "MANGA")
        variables = {"id": mal_id, "type": mtype}
        time.sleep(1)
        logger.info(f"Requesting Anilist ID for {mtype} {mal_id}")
        response = requests.post(
            GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        if response.status_code > 400 and response.status_code < 500:
            logger.warning(f"Anilist returned {response.status_code}, not found")
            return None
        data: Dict[str, Any] = response.json()["data"]["Media"]
        return data

    @staticmethod
    def is_404(summary: Summary | None) -> bool:
        if summary is None:
            return True
        if "error" in summary.metadata:
            return bool(summary.metadata["error"] == 404)
        return False

    def request_data(self, url: str, preprocess_url: bool = True) -> Summary:
        if preprocess_url:
            uurl = self.preprocess_url(url)
        else:
            uurl = url
        del url
        mal_id = int(uurl.split("/")[-1])
        media_type = uurl.split("/")[-2]
        anilist_data = self.fetch_anilist_data(mal_id, media_type)
        if anilist_data is None:
            return Summary(
                url=uurl,
                data={},
                metadata={"error": 404},
                timestamp=datetime.now(),
            )
        return Summary(
            url=uurl, data={}, metadata=anilist_data, timestamp=datetime.now()
        )

    def refresh_data(self, url: str) -> Summary:
        uurl = self.preprocess_url(url)
        summary = self.request_data(uurl, preprocess_url=False)
        self.summary_cache.put(uurl, summary)
        return summary

    def refresh_if_404(self, url: str) -> Summary | None:
        uurl = self.preprocess_url(url)
        if self.is_404(self.summary_cache.get(uurl)):
            return self.refresh_data(uurl)
        return self.summary_cache.get(uurl)


@cache
def anilist_cache() -> AnilistCache:
    return AnilistCache()
