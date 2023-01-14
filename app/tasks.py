from typing import Dict, Any, List
from datetime import datetime
from asyncio import sleep

from src.log import logger

from fastapi import APIRouter, Depends
from sqlalchemy import select
from pydantic import BaseModel
from sqlmodel import Session

from app.db import Task, EntryType, TaskType, get_db, data_engine

router = APIRouter()


@router.get("/full_database_update")
async def full_update():
    """
    this is expensive! -- only do this when necessary

    happens once every 10 minutes, pinged from the ./update_data script
    after other stuff has been updated
    """
    from app.db_entry_update import update_database

    await update_database()


@router.get("/refresh_entry")
async def refresh_entry(
    task_type: TaskType, entry_type: EntryType, entry_id: int, sess=Depends(get_db)
) -> str:
    """
    adds a request to update an entry to the database
    """
    sess.add(
        Task(
            task_type=task_type,
            task_data={"entry_type": entry_type.value, "entry_id": entry_id},
        )
    )
    sess.commit()
    return "added to queue"


class TaskRead(BaseModel):
    id: int
    task_type: TaskType
    task_data: Dict[str, Any]
    added_at: datetime


@router.get("/list_queue")
async def list_queue(sess=Depends(get_db)) -> List[TaskRead]:
    return list(sess.query(Task).all())


async def process_queue(count: int = 10) -> None:
    logger.info("processing queue...")

    with Session(data_engine) as sess:
        tasks = [row[0] for row in sess.exec(select(Task).limit(count))]

    if len(tasks) == 0:
        logger.info("no tasks to process")
        return

    for task in tasks:
        logger.info(f"processing task {task}")
        match task.task_type:
            case TaskType.REFRESH_ENTRY:
                from .db_entry_update import refresh_entry

                await refresh_entry(
                    entry_id=task.task_data["entry_id"],
                    entry_type=task.task_data["entry_type"],
                )

            case _:
                logger.error(f"unknown task type {task.task_type}")

        with Session(data_engine) as sess:
            sess.delete(task)
            sess.commit()
