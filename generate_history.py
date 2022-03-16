import os
import json
import io
import time
from pathlib import Path
from datetime import datetime, date
from typing import NamedTuple, Iterator, Any
from dataclasses import dataclass

import backoff
import click
import orjson
import requests
from git.objects import Tree
from git.objects.commit import Commit
from git.repo.base import Repo
from malexport.parse.common import parse_date_safe
from malexport.exporter.mal_session import MalSession

this_dir = Path(__file__).parent.absolute()
mal_id_cache_dir = this_dir / "mal-id-cache"
assert mal_id_cache_dir.exists()

linear_history_file = this_dir / "linear_history.json"
anime_cachefile = this_dir / "anime_info.json"
manga_cachefile = this_dir / "manga_info.json"


@dataclass
class Entry:
    entry_id: int
    e_type: str
    is_nsfw: bool
    dt: datetime
    action: bool = True  # true - added, false - removed


JsonData = dict[str, list[int]]


class Snapshot(NamedTuple):
    data: JsonData
    entry_type: str
    dt: datetime


ANIME_EXPECTED = ["cache/anime_cache.json", "anime_cache.json", "cache.json"]
MANGA_EXPECTED = ["cache/manga_cache.json", "manga_cache.json"]


def _get_blob(tree: Tree, keys: list[str]) -> JsonData | None:
    for expected in keys:
        try:
            blob = tree / expected
            buf = io.BytesIO(blob.data_stream.read()).read().decode("utf-8")
            if buf.strip() == "":
                continue
            return orjson.loads(buf)
        except KeyError:
            continue
        except orjson.JSONDecodeError:
            continue
    return None


def to_utc(dt: datetime) -> datetime:
    return datetime.fromtimestamp(dt.timestamp())


def snapshot_commit(commit: Commit) -> Iterator[Snapshot]:
    if anime := _get_blob(commit.tree, ANIME_EXPECTED):
        assert set(anime.keys()) == {"nsfw", "sfw"}
        yield Snapshot(anime, "anime", dt=to_utc(commit.authored_datetime))
    if manga := _get_blob(commit.tree, MANGA_EXPECTED):
        assert set(manga.keys()) == {"nsfw", "sfw"}
        yield Snapshot(manga, "manga", dt=to_utc(commit.authored_datetime))


def iter_snapshots(repo: Path) -> Iterator[Snapshot]:
    r = Repo(str(repo))
    commits = list(r.iter_commits())
    commits.sort(key=lambda c: c.committed_date)
    for c in commits:
        yield from snapshot_commit(c)


def track_diffs() -> Iterator[Entry]:
    anime: set[int] = set()
    manga: set[int] = set()
    for sn in iter_snapshots(mal_id_cache_dir):
        assert sn.entry_type in {"anime", "manga"}
        state = anime if sn.entry_type == "anime" else manga
        sfw = set(sn.data["sfw"])
        nsfw = set(sn.data["nsfw"])

        for is_nsfw in [True, False]:
            source = nsfw if is_nsfw else sfw
            # source_combined = set(nsfw.union(sfw))

            # check if any items in the new 'source'
            # aren't already in state
            for mal_id in source:
                if mal_id in state:
                    continue
                else:
                    state.add(mal_id)
                    yield Entry(
                        entry_id=mal_id,
                        e_type=sn.entry_type,
                        is_nsfw=is_nsfw,
                        dt=sn.dt,
                    )

            # for some reason this doesnt work?
            # makes lots of entries appear 20+ times
            # check if any items in the current state aren't
            # in the source (new items)
            # for mal_id in list(state):
            #    if mal_id not in source_combined:
            #        yield Entry(
            #            entry_id=mal_id,
            #            e_type=sn.entry_type,
            #            is_nsfw=is_nsfw,
            #            dt=sn.dt,
            #            action=False,
            #        )
            #        state.remove(mal_id)
            #        assert mal_id not in state


@click.group()
def main() -> None:
    pass


@main.command(short_help="create timeline using git history")
def linear_history() -> None:
    """Create a big yaml file with dates based on the git timestamps for when entries were added to cache"""
    for d in track_diffs():
        print(orjson.dumps(d).decode("utf-8"))


def read_linear_history() -> list[Any]:
    with open(linear_history_file) as f:
        data = orjson.loads(f.read())
    return data


def _get_img(data: dict) -> str | None:
    if img := data.get("medium"):
        return img
    if img := data.get("large"):
        return img
    return None


def _anime_data() -> dict[str, Any]:
    anime_data = {}
    if anime_cachefile.exists():
        anime_data = orjson.loads(anime_cachefile.read_text())
    return anime_data


def _manga_data() -> dict[str, Any]:
    manga_data = {}
    if manga_cachefile.exists():
        manga_data = orjson.loads(manga_cachefile.read_text())
    return manga_data


@main.command(short_help="use malexport data from my list")
def local_cache() -> None:
    try:
        del os.environ["MAL_USERNAME"]
        del os.environ["MALEXPORT_COMBINE_FILTER_TAGS"]
    except Exception as e:
        print(str(e))
    from my.mal.export import anime, manga

    anime_data = _anime_data()

    for a in anime():
        assert a.XMLData
        assert a.APIList
        anime_data[str(a.id)] = {
            "media_type": a.APIList.media_type,
            "title": a.XMLData.title,
            "img": _get_img(a.APIList.main_picture),
            "mean": a.APIList.mean,
            "popularity": a.APIList.popularity,
            "start_date": str(a.XMLData.start_date) if a.XMLData else None,
        }

    anime_cachefile.write_text(json.dumps(anime_data))

    manga_data = _manga_data()

    for m in manga():
        assert m.XMLData
        assert m.APIList
        manga_data[str(m.id)] = {
            "media_type": m.APIList.media_type,
            "title": m.XMLData.title,
            "img": _get_img(m.APIList.main_picture),
            "mean": m.APIList.mean,
            "popularity": m.APIList.popularity,
            "start_date": str(m.APIList.start_date) if m.APIList.start_date else None,
        }

    manga_cachefile.write_text(json.dumps(manga_data))


@backoff.on_exception(
    lambda: backoff.constant(1), requests.exceptions.RequestException, max_tries=3
)
def api_request(session: MalSession, url: str) -> Any:
    time.sleep(1)
    resp: requests.Response = session.session.get(url)
    resp.raise_for_status()
    return resp.json()


@main.command(short_help="update using API")
def remote_update() -> None:
    from malexport.exporter.account import Account
    from malexport.exporter.mal_session import MalSession

    BASE_URL = "https://api.myanimelist.net/v2/{etype}/{mal_id}?nsfw=true&fields=id,title,main_picture,alternative_titles,start_date,end_date,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,created_at,updated_at,media_type,status,genres,my_list_status,num_episodes,start_season,broadcast,source,average_episode_duration,rating,pictures,background,related_anime,related_manga,recommendations,studios,statistics"

    assert "MAL_USERNAME" in os.environ
    acc = Account.from_username(os.environ["MAL_USERNAME"])
    acc.mal_api_authenticate()
    assert acc.mal_session is not None
    session: MalSession = acc.mal_session

    # not using safe_request, so lets just refresh when we call this
    session.refresh_token()

    hist = read_linear_history()

    anime_data = _anime_data()
    manga_data = _manga_data()

    try:
        for hs in hist:
            sid = str(hs["entry_id"])
            stype = hs["e_type"]
            write_to = anime_data if stype == "anime" else manga_data
            if sid not in write_to:
                try:
                    click.echo(f"Requesting {stype}/{sid}")
                    data = api_request(
                        session, BASE_URL.format(etype=stype, mal_id=sid)
                    )
                    start_date: date | None = parse_date_safe(data.get("start_date"))
                    start_date_str = str(start_date) if start_date is not None else None
                    write_to[sid] = {
                        "media_type": data["media_type"],
                        "title": data["title"],
                        "img": _get_img(data.get("main_picture", {})),
                        "mean": data.get("mean"),
                        "popularity": int(data["popularity"]),
                        "start_date": start_date_str,
                    }
                    print(write_to[sid])
                except requests.exceptions.RequestException:
                    # entry doesnt exist anymore?
                    click.echo("Couldn't cache info, assuming this a deleted entry?")
                    write_to[sid] = None
                    click.echo(f"could not cache {stype}/{sid} ({hs})", err=True)
    except KeyboardInterrupt:
        pass

    anime_cachefile.write_text(json.dumps(anime_data))
    manga_cachefile.write_text(json.dumps(manga_data))


if __name__ == "__main__":
    main(prog_name="traverse_history")
