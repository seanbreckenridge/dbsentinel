import logging
from pathlib import Path

import orjson
import click

from mal_id.metadata_cache import request_metadata
from mal_id.linear_history import track_diffs, read_linear_history
from mal_id.ids import approved_ids, unapproved_ids, estimate_all_users_max, _estimate_page
from mal_id.index_requests import request_pages, currently_requesting, queue
from mal_id.paths import sqlite_db_path


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logs")
def main(debug: bool) -> None:
    if debug:
        import mal_id.log

        mal_id.log.logger = mal_id.log.setup(level=logging.DEBUG)


@main.command(short_help="create timeline using git history")
def linear_history() -> None:
    """Create a big json file with dates based on the git timestamps for when entries were added to cache"""
    for d in track_diffs():
        print(orjson.dumps(d).decode("utf-8"))


@main.command(short_help="request missing data using API")
@click.option("--request-failed", is_flag=True, help="re-request failed entries")
def update_metadata(request_failed: bool) -> None:
    """
    request missing entry metadata using MAL API
    """
    for hs in read_linear_history():
        request_metadata(hs["entry_id"], hs["e_type"], rerequest_failed=request_failed)

    unapproved = unapproved_ids()
    for aid in unapproved.anime:
        request_metadata(aid, "anime", rerequest_failed=request_failed)

    for mid in unapproved.manga:
        request_metadata(mid, "manga", rerequest_failed=request_failed)


@main.command(short_help="print approved/unapproved counts")
def counts() -> None:
    """
    print approved/unapproved counts for anime/manga
    """
    a = approved_ids()
    u = unapproved_ids()
    click.echo(f"Approved anime: {len(a.anime)}")
    click.echo(f"Approved manga: {len(a.manga)}")
    click.echo(f"Unapproved anime: {len(u.anime)}")
    click.echo(f"Unapproved manga: {len(u.manga)}")


@main.command(short_help="print page ranges from indexer")
def pages() -> None:
    """
    print page ranges from indexer
    """
    click.echo("currently requesting: {}".format(currently_requesting()))
    click.echo("queue: {}".format(queue()))


@main.command(short_help="use user lists to find out if new entries have been approved")
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
        click.echo(
            f"should check {check_pages} {list_type} pages".format(check_pages),
            err=True,
        )
    if request:
        if check_pages == 0:
            click.echo("no new entries found, skipping request")
            return
        if timid:
            cur = currently_requesting()
            if cur is not None:
                click.echo(f"timid: currently requesting {cur}, skipping request")
                return
        request_pages(list_type, check_pages)


@main.command(short_help="estimate which page to check for an ID")
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


@main.group()
def server() -> None:
    """app/server related commands"""


@server.command(short_help="initialize database")
def initialize_db() -> None:
    """initialize database"""
    from app.db import init_db
    from app.db_entry_update import update_database
    from asyncio import run

    init_db()
    run(update_database())


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
