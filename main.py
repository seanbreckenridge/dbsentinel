import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional

import click

from mal_id.metadata_cache import request_metadata, has_metadata
from mal_id.linear_history import track_diffs, iter_linear_history
from mal_id.ids import (
    unapproved_ids,
    estimate_all_users_max,
    _estimate_page,
    approved_ids,
)
from mal_id.index_requests import request_pages, currently_requesting, queue
from mal_id.paths import (
    linear_history_unmerged,
    linear_history_cleaned,
    my_animelist_xml,
    sqlite_db_path,
)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logs")
def main(debug: bool) -> None:
    if debug:
        import mal_id.log

        mal_id.log.logger = mal_id.log.setup(level=logging.DEBUG)


@main.group(short_help="relating to myanimelist/ids")
def mal() -> None:
    pass


@mal.command(short_help="create timeline using git history")
def linear_history() -> None:
    """Create a big json file with dates based on the git timestamps for when entries were added to cache"""
    for d in track_diffs():
        print(json.dumps(d.to_dict()))


@mal.command(short_help="remove duplicate JSON data in linear history")
def clean_linear_history() -> None:
    from collections import defaultdict
    from typing import List, Mapping, Tuple

    import orjson

    from mal_id.linear_history import Entry

    merged: List[Entry] = []
    # create a map from ID -> List[Entry]
    history_map: Mapping[Tuple[int, str], List[Entry]] = defaultdict(list)

    # read and group entries by ID/type
    with linear_history_unmerged.open("r") as f:
        for line in f:
            ent = Entry.from_dict(orjson.loads(line))
            history_map[(ent.entry_id, ent.e_type)].append(ent)

    for entries in history_map.values():
        # sort by date
        entries.sort(key=lambda e: e.dt)

        for e in entries:
            if e.action is True:
                merged.append(e)
                break

        for e in reversed(entries):
            if e.action is False:
                merged.append(e)
                break

    # sort by date
    merged.sort(key=lambda e: e.dt)

    with linear_history_cleaned.open("wb") as w:
        for entry in merged:
            w.write(orjson.dumps(entry.to_dict()))
            w.write(b"\n")


@mal.command(short_help="make sure MAL is not down")
def check_mal() -> None:
    from mal_id.metadata_cache import check_mal as heartbeat

    if not heartbeat():
        sys.exit(1)


@mal.command(short_help="request missing data using API")
@click.option("--request-failed", is_flag=True, help="re-request failed entries")
@click.option(
    "--print-missing", is_flag=True, help="print missing entries instead of requesting"
)
def update_metadata(request_failed: bool, print_missing: bool) -> None:
    """
    request missing entry metadata using MAL API
    """
    from mal_id.metadata_cache import check_mal as heartbeat

    total_missing = 0

    if not heartbeat():
        sys.exit(1)

    for hs in iter_linear_history():
        if print_missing and not has_metadata(hs.entry_id, hs.e_type):
            total_missing += 1
            click.echo(f"{hs.entry_id} {hs.e_type}")
        else:
            request_metadata(hs.entry_id, hs.e_type, rerequest_failed=request_failed)

    unapproved = unapproved_ids()
    for aid in unapproved.anime:
        if print_missing and not has_metadata(aid, "anime"):
            total_missing += 1
            click.echo(f"{aid} anime")
        else:
            request_metadata(aid, "anime", rerequest_failed=request_failed)

    for mid in unapproved.manga:
        if print_missing and not has_metadata(mid, "manga"):
            total_missing += 1
            click.echo(f"{mid} manga")
        else:
            request_metadata(mid, "manga", rerequest_failed=request_failed)

    if print_missing:
        click.echo(f"total missing: {total_missing}")


@mal.command(short_help="run a full db update")
@click.option(
    "--rerequest-oldest",
    type=int,
    default=None,
    help="rerequest and update data for oldest N entries",
)
def full_db_update(rerequest_oldest: Optional[int]) -> None:
    """
    this is expensive! -- only do this when necessary

    this reads all the cached data and updates the sqlite db
    """
    from mal_id.metadata_cache import check_mal as heartbeat

    if not heartbeat():
        sys.exit(1)

    from app.db_entry_update import update_database

    click.echo("running full db update...")
    asyncio.run(update_database(update_outdated_metadata=rerequest_oldest))
    click.echo("done")


@mal.command(short_help="print page ranges from indexer")
def pages() -> None:
    """
    print page ranges from indexer
    """
    click.echo("currently requesting: {}".format(currently_requesting()))
    click.echo("queue: {}".format(queue()))


def _request_pages(
    *,
    check_pages: int,
    list_type: str,
    request: bool,
    timid: bool,
) -> None:
    if check_pages == 0:
        click.echo("no new entries found, skipping request", err=True)
        return

    click.echo(
        f"should check {check_pages} {list_type} pages",
        err=True,
    )

    if request:
        if timid:
            cur = currently_requesting()
            if cur is not None:
                click.echo(
                    f"timid: currently requesting {cur}, skipping request", err=True
                )
                return
        request_pages(list_type, check_pages)


@mal.command(short_help="use user lists to find out if new entries have been approved")
@click.option("--list-type", type=click.Choice(["anime", "manga"]), default="anime")
@click.option("--request", is_flag=True, help="request new entries")
@click.option(
    "--timid", is_flag=True, help="only request new entries if not already requesting"
)
@click.option(
    "--print-url",
    is_flag=True,
    default=False,
    help="print corresponding checker_mal url query params",
)
@click.argument("USERNAMES", type=click.Path(exists=True))
def estimate_user_recent(
    usernames: str, request: bool, timid: bool, list_type: str, print_url: bool
) -> None:
    check_usernames = list(
        filter(
            lambda ln: ln.strip(),
            map(str.strip, Path(usernames).read_text().strip().splitlines()),
        )
    )
    assert len(check_usernames) > 0
    check_pages = estimate_all_users_max(check_usernames, list_type)

    if print_url and check_pages > 0:
        click.echo(f"type={list_type}&pages={check_pages}")
    else:
        _request_pages(
            check_pages=check_pages, list_type=list_type, request=request, timid=timid
        )


@mal.command(short_help="use animelist xml to find deleted entries")
@click.option("--request", is_flag=True, help="request new entries")
@click.option(
    "--timid", is_flag=True, help="only request new entries if not already requesting"
)
def estimate_deleted_animelist_xml(request: bool, timid: bool) -> None:
    from mal_id.ids import estimate_deleted_entry

    check_pages = estimate_deleted_entry(my_animelist_xml)
    _request_pages(
        check_pages=check_pages, list_type="anime", request=request, timid=timid
    )


@mal.command(short_help="estimate which page to check for an ID")
@click.option(
    "-e",
    "--entry-type",
    type=click.Choice(["anime", "manga"]),
    required=True,
    default="anime",
)
@click.argument("MAL_ID", type=int)
def estimate_page(entry_type: str, mal_id: int) -> None:
    click.echo(
        _estimate_page(
            mal_id, list(reversed(sorted(getattr(approved_ids(), entry_type))))
        )
    )


@main.group("dbs", short_help="for interacting with other dbs")
def dbs() -> None:
    """
    e.g. anilist, syobocal
    """
    pass


@dbs.command(short_help="update anilist ids")
@click.option("--only", type=click.Choice(["anime", "manga"]), default=None)
def anilist_update(only: str) -> None:
    """
    update anilist ids
    """
    from mal_id.anilist_cache import AnilistCache
    from mal_id.ids import approved_ids

    ac = AnilistCache()

    approved = approved_ids()

    if only is None or only == "anime":
        for mal_id in approved.anime:
            ac.get("https://myanimelist.net/anime/{}".format(mal_id))

    if only is None or only == "manga":
        for mal_id in approved.manga:
            ac.get("https://myanimelist.net/manga/{}".format(mal_id))


@dbs.command(short_help="print syobocal urls which have MAL urls")
def dump_syobocal() -> None:
    from mal_id.arm import mal_arm_dict

    for mal_id, arm_obj in mal_arm_dict().items():
        if arm_obj.syobocal_tid is not None:
            click.echo(f"{mal_id} => {arm_obj.syobocal_url}")


@main.group()
def server() -> None:
    """app/server related commands"""


@server.command(short_help="initialize database")
@click.option(
    "--refresh-images",
    is_flag=True,
    default=False,
    help="refresh images which couldn't be cached",
)
@click.option(
    "--force-update-db",
    is_flag=True,
    default=False,
    help="force update database even when entry data already exists",
)
@click.option(
    "--skip-proxy-images",
    is_flag=True,
    default=False,
    help="skip proxying images to S3",
)
def initialize_db(
    refresh_images: bool, force_update_db: bool, skip_proxy_images: bool
) -> None:
    """initialize database"""
    from app.db import init_db
    from app.db_entry_update import update_database
    from asyncio import run

    init_db()
    run(
        update_database(
            refresh_images=refresh_images,
            force_update_db=force_update_db,
            skip_proxy_images=skip_proxy_images,
        )
    )


@server.command(short_help="generate media types for frontend")
@click.argument("OUTPUT", type=click.Path(path_type=Path))
def generate_media_types(output: Path) -> None:
    from app.db import AnimeMetadata, MangaMetadata, data_engine, Session
    from sqlmodel.sql.expression import select
    from sqlalchemy import func

    with Session(data_engine) as sess:
        anime_types = list(filter(lambda a: a is not None, sess.exec(select(func.distinct(AnimeMetadata.media_type))).all()))  # type: ignore
        manga_types = list(filter(lambda a: a is not None, sess.exec(select(func.distinct(MangaMetadata.media_type))).all()))  # type: ignore

    output.write_text(
        json.dumps(
            {
                "anime": sorted(anime_types),
                "manga": sorted(manga_types),
            }
        )
    )

    click.echo("anime types: {}".format(anime_types))
    click.echo("manga types: {}".format(manga_types))


@server.command()
def delete_database() -> None:
    """Delete the sqlite database"""
    if sqlite_db_path.exists():
        click.echo("Unlinking database...")
        sqlite_db_path.unlink()
    else:
        click.echo("Database doesn't exist...")


if __name__ == "__main__":
    main(prog_name="generate_history")
