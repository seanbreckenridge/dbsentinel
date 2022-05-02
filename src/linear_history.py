import io
from pathlib import Path
from datetime import datetime
from typing import NamedTuple, Iterator, Set
from dataclasses import dataclass

import orjson
from git.objects import Tree
from git.objects.commit import Commit
from git.repo.base import Repo

from src.paths import mal_id_cache_dir
from src.common import to_utc


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
        #    if mal_id not in sfw and mal_id not in nsfw:
        #        yield Entry(
        #            entry_id=mal_id,
        #            e_type=sn.entry_type,
        #            is_nsfw=None,
        #            dt=sn.dt,
        #            action=False,
        #        )
        #        state.remove(mal_id)
        #        assert mal_id not in state


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
