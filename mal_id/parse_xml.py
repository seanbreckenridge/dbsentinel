from typing import Set
from pathlib import Path

from malexport.parse.xml import parse_xml


def parse_user_ids(xml_file: Path) -> Set[int]:
    return {ent.id for ent in parse_xml(xml_file).entries}
