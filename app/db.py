import enum
from typing import Iterator, Optional
from datetime import datetime, date

from sqlmodel import SQLModel, Field, create_engine, Session  # type: ignore[import]

from src.metadata_cache import request_metadata
from src.ids import approved_ids, unapproved_ids
from src.log import logger
from src.paths import sqlite_db_uri

from app.settings import settings


class Status(str, enum.Enum):
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    DELETED = "deleted"
    UNSET = "unset"


class NSFW(str, enum.Enum):
    WHITE = "white"
    BLACK = "black"
    GRAY = "gray"
    GREY = "gray"


class EntryStatus(SQLModel, table=False):
    # primary key/unique id
    type_id: str = Field(str, primary_key=True)  # e.g. anime_1, manga_2

    # approved status of the entry
    approved_status: Status = Field(defualt=Status.UNAPPROVED)
    approved_at: Optional[datetime] = Field(default=None)


class EntryMetadata(EntryStatus, table=False):
    # shared
    id: int
    title: str
    picture_url: str
    start_date: date
    end_date: date
    synopsis: str
    mean: Optional[float]
    list_users: int
    list_scored_by: int
    nsfw: NSFW
    created_at: datetime
    updated_at: datetime
    media_type: str
    status: str
    genres: str  # stored as JSON
    rating: Optional[str]

    # anime
    num_episodes: Optional[int]
    start_season: Optional[str]
    source: Optional[str]
    average_ep_duration: Optional[int]

    # manga
    # TODO: need to add manga fields to API request?
    # and remove my_list_status


data_engine = create_engine(sqlite_db_uri, echo=settings.SQL_ECHO)


def init_db() -> None:
    logger.info("Creating tables...")
    SQLModel.metadata.create_all(data_engine)


def get_db() -> Iterator[Session]:
    with Session(data_engine) as session:
        yield session


def update_database():
    pass
