from pathlib import Path

root_dir = Path(__file__).parent.parent.absolute()
data_dir = root_dir / "data"
if not data_dir.exists():
    data_dir.mkdir(parents=True)
mal_id_cache_dir = data_dir / "mal-id-cache"
assert mal_id_cache_dir.exists()

linear_history_unmerged = data_dir / "data.jsonl"
linear_history_file = data_dir / "linear_history.json"
metadatacache_dir = data_dir / "metadata"

arm_dir = data_dir / 'arm'
assert arm_dir.exists()

anilist_cache = data_dir / "anilist_cache"

sqlite_db_path = data_dir / "data.sqlite"
sqlite_db_uri = "sqlite:///{}".format(sqlite_db_path.absolute())

unapproved_dir = data_dir / "unapproved"
if not unapproved_dir.exists():
    unapproved_dir.mkdir(parents=True)

unapproved_anime_path = unapproved_dir / "anime.json"
unapproved_manga_path = unapproved_dir / "manga.json"

image_data = data_dir / "image_info.json"
