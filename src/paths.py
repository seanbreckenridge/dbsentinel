from pathlib import Path

roor_dir = Path(__file__).parent.parent.absolute()
data_dir = roor_dir / "data"
if not data_dir.exists():
    data_dir.mkdir(parents=True)
mal_id_cache_dir = data_dir / "mal-id-cache"
assert mal_id_cache_dir.exists()

linear_history_file = data_dir / "linear_history.json"
metadatacache_dir = data_dir / "metadata"
