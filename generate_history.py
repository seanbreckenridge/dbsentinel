import orjson
import click
from typing import Any

from src.paths import linear_history_file
from src.metadata_cache import MetadataCache
from src.linear_history import track_diffs


@click.group()
def main() -> None:
    pass


@main.command(short_help="create timeline using git history")
def linear_history() -> None:
    """Create a big json file with dates based on the git timestamps for when entries were added to cache"""
    for d in track_diffs():
        print(orjson.dumps(d).decode("utf-8"))


def read_linear_history() -> list[Any]:
    with open(linear_history_file) as f:
        data = orjson.loads(f.read())
    return data


@main.command(short_help="update using API")
@click.option("--request-failed", is_flag=True, help="re-request failed entries")
def update_metadata(request_failed: bool) -> None:

    mcache = MetadataCache()
    for hs in read_linear_history():
        sid = str(hs["entry_id"])
        stype = hs["e_type"]
        api_url = mcache.__class__.BASE_URL.format(etype=stype, mal_id=sid)
        if not mcache.in_cache(api_url):
            mcache.get(api_url)
        elif request_failed:
            sdata = mcache.get(api_url)
            if sdata.metadata == {}:
                mcache.logger.info("re-requesting failed entry")
                mcache.refresh_data(api_url)


if __name__ == "__main__":
    main(prog_name="generate_history")
