from pathlib import Path

this_dir = Path(__file__).parent.parent.absolute()
mal_id_cache_dir = this_dir / "mal-id-cache"
assert mal_id_cache_dir.exists()

linear_history_file = this_dir / "linear_history.json"
metadatacache_dir = this_dir / "metadata"
