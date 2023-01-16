import orjson
from mal_id.paths import arm_dir
from pydantic import BaseModel


arm_file = (arm_dir / "arm.json").absolute()
assert arm_file.exists()


class Arm(BaseModel):
    mal_id: int | None
    anilist_id: int | None
    annict_id: int | None
    syobocal_tid: int | None

    @property
    def syobocal_url(self) -> str:
        return f"https://cal.syoboi.jp/tid/{self.syobocal_tid}"


def arm_dump(filter_mal_id: bool = True) -> list[Arm]:
    data = orjson.loads(arm_file.read_bytes())
    objs = [Arm.parse_obj(v) for v in data]
    if filter_mal_id:
        objs = [v for v in objs if v.mal_id is not None]
    return objs


def mal_arm_dict() -> dict[int, Arm]:
    return {v.mal_id: v for v in arm_dump(filter_mal_id=True) if v.mal_id is not None}
