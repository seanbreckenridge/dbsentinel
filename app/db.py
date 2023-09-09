import enum
from typing import Iterator, Optional, Dict, Any
from datetime import datetime, date

from sqlmodel import SQLModel, Field, create_engine, Session, Column, JSON

from mal_id.log import logger
from mal_id.paths import sqlite_db_uri

from app.settings import settings


class Status(str, enum.Enum):
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    DELETED = "deleted"
    DENIED = "denied"


class EntryType(str, enum.Enum):
    ANIME = "anime"
    MANGA = "manga"

    @classmethod
    def from_str(cls, label: str) -> "EntryType":
        ll = label.lower()
        if ll == "anime":
            return cls.ANIME
        elif ll == "manga":
            return cls.MANGA
        else:
            raise ValueError(f"Invalid label: {label}")


class ApprovedBase(SQLModel, table=False):
    # approved status of the entry
    id: int = Field(primary_key=True)
    title: str
    nsfw: Optional[bool]
    json_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    approved_status: Status = Field(default=Status.UNAPPROVED)
    media_type: Optional[str] = Field(default=None)
    member_count: Optional[int] = Field(default=None)
    average_episode_duration: Optional[int] = Field(default=None)
    # when the entry was approved/denied/deleted etc.
    status_changed_at: datetime
    # when metadata for this was updated
    updated_at: datetime
    start_date: Optional[date]
    end_date: Optional[date]


class AnimeMetadata(ApprovedBase, table=True):
    pass


class MangaMetadata(ApprovedBase, table=True):
    pass


class ProxiedImage(SQLModel, table=True):
    mal_id: int = Field(primary_key=True)
    mal_entry_type: EntryType = Field(primary_key=True)
    mal_url: str = Field(index=True)
    proxied_url: str = Field(index=True)


class AnilistId(SQLModel, table=True):
    mal_id: int = Field(primary_key=True)
    entry_type: EntryType = Field(primary_key=True)
    anilist_id: int = Field()


connect_args = {"check_same_thread": False, "timeout": 15}
data_engine = create_engine(
    sqlite_db_uri, echo=settings.SQL_ECHO, connect_args=connect_args
)


def init_db() -> None:
    logger.info("Creating tables...")
    SQLModel.metadata.create_all(data_engine)


def get_db() -> Iterator[Session]:
    with Session(data_engine) as session:
        yield session
