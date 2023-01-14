import enum
from typing import Iterator, Optional, Dict, Any
from datetime import datetime, date

from sqlmodel import SQLModel, Field, create_engine, Session, Column, JSON

from src.log import logger
from src.paths import sqlite_db_uri

from app.settings import settings


class Status(str, enum.Enum):
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    DELETED = "deleted"
    DENIED = "denied"


class ApprovedData(SQLModel, table=False):
    # approved status of the entry
    approved_status: Status = Field(default=Status.UNAPPROVED)
    approved_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


class AnimeMetadata(ApprovedData, table=True):
    id: int = Field(primary_key=True)
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    nsfw: bool = Field(default=False)
    json_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class MangaMetadata(ApprovedData, table=True):
    id: int = Field(primary_key=True)
    title: str
    start_date: Optional[date]
    end_date: Optional[date]
    nsfw: bool = Field(default=False)
    json_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class EntryType(str, enum.Enum):
    ANIME = "anime"
    MANGA = "manga"


class TaskType(str, enum.Enum):
    FULL_DB_UPDATE = "full_db_update"
    REFRESH_ENTRY = "refresh_entry"


class Task(SQLModel, table=True):
    id: int = Field(primary_key=True)
    task_type: TaskType
    task_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    added_at: datetime = Field(default_factory=datetime.now)


connect_args = {"check_same_thread": False}
data_engine = create_engine(
    sqlite_db_uri, echo=settings.SQL_ECHO, connect_args=connect_args
)


def init_db() -> None:
    logger.info("Creating tables...")
    SQLModel.metadata.create_all(data_engine)


def get_db() -> Iterator[Session]:
    with Session(data_engine) as session:
        yield session
