import io
from pathlib import Path
from datetime import datetime, timezone
from typing import NamedTuple, Iterator, Any

import orjson
from git.objects import Tree
from git.objects.commit import Commit
from git.repo.base import Repo

from mal_id.paths import mal_id_cache_dir, linear_history_cleaned
from mal_id.common import to_utc


class Entry(NamedTuple):
    entry_id: int
    e_type: str
    dt: datetime
    action: bool  # true - added, false - removed

    @classmethod
    def from_dict(cls, d: dict) -> "Entry":
        return cls(
            entry_id=d["entry_id"],
            e_type=d["e_type"],
            dt=datetime.fromtimestamp(d["dt"], tz=timezone.utc),
            action=d["action"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "e_type": self.e_type,
            "dt": self.dt.timestamp(),
            "action": self.action,
        }

    @property
    def key(self) -> str:
        assert isinstance(self.entry_id, int)
        assert self.e_type in {"anime", "manga"}
        return f"{self.e_type}_{self.entry_id}"


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
            data = orjson.loads(buf)
            assert isinstance(data, dict)
            return data
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
        ids_at_this_commit = set(sn.data["sfw"] + sn.data["nsfw"])

        # check if any that are in this commit aren't already 'approved' at this time
        # aren't already in state
        for mal_id in ids_at_this_commit:
            # already approved
            if mal_id in state:
                continue
            else:
                # this was just approved, add it to state and yield an event
                state.add(mal_id)
                yield Entry(
                    entry_id=mal_id, e_type=sn.entry_type, dt=sn.dt, action=True
                )

        # check if any of the items in state...
        #
        # hmmm -- this seems to add a bunch of duplicates?
        # but it does work fine for what we want to do, so I think its fine
        #
        # this is shrunk in main.py mal clean-linear-history by
        # only retaining the first and last time an approved/deleted pair appears in history,
        # since that's all we want from the git state
        for mal_id in list(state):
            # are not in this commit...
            if mal_id not in ids_at_this_commit:
                yield Entry(
                    entry_id=mal_id,
                    e_type=sn.entry_type,
                    dt=sn.dt,
                    action=False,
                )
                state.remove(mal_id)
                assert mal_id not in state


def iter_linear_history() -> Iterator[Entry]:
    with open(linear_history_cleaned, "rb") as f:
        for line in f:
            yield Entry.from_dict(orjson.loads(line))
