"""
Interact with the /api/pages index endpoint.
https://github.com/Hiyori-API/checker_mal
"""

from typing import NamedTuple, Dict, Any, Optional, List, cast

import requests

from mal_id.log import logger

INDEX_BASE = "http://localhost:4001/api"


def _debug() -> Dict[str, Any]:
    debug_url = f"{INDEX_BASE}/debug"
    req = requests.get(debug_url)
    req.raise_for_status()
    return cast(Dict[str, Any], req.json())


class Index(NamedTuple):
    list_type: str
    page_count: int


def currently_requesting() -> Optional[Index]:
    debug = _debug()
    if "current_request" not in debug:
        return None
    cur = debug["current_request"]
    if not cur:
        return None
    assert "timeframe" in cur
    assert "type" in cur
    assert cur["type"] in {"anime", "manga"}
    return Index(
        list_type=cur["type"],
        page_count=cur["timeframe"],
    )


def queue() -> List[Index]:
    debug = _debug()
    assert "requests" in debug
    reqs = []
    for list_type, count in debug["requests"]:
        assert list_type in {"anime", "manga"}
        assert count > 0
        reqs.append(Index(list_type=list_type, page_count=count))
    return reqs


def request_pages(list_type: str, check_pages: int) -> None:
    url = f"{INDEX_BASE}/pages?type={list_type}&pages={check_pages}"
    logger.info(f"requesting {url}")
    resp = requests.get(url)
    resp.raise_for_status()
