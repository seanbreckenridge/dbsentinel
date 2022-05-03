import logging
from typing import Any

import orjson
import click

from src.paths import linear_history_file
from src.metadata_cache import request_metadata
from src.linear_history import track_diffs
from src.ids import approved_ids, unapproved_ids


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logs")
def main(debug: bool) -> None:
    if debug:
        import src.log

        src.log.logger = src.log.setup(level=logging.DEBUG)


@main.command(short_help="create timeline using git history")
def linear_history() -> None:
    """Create a big json file with dates based on the git timestamps for when entries were added to cache"""
    for d in track_diffs():
        print(orjson.dumps(d).decode("utf-8"))


def read_linear_history() -> list[Any]:
    with open(linear_history_file) as f:
        data = orjson.loads(f.read())
    return data


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


if __name__ == "__main__":
    main(prog_name="generate_history")
