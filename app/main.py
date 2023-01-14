import os
from fastapi import FastAPI


def create_app() -> FastAPI:
    current_app = FastAPI(title="malsentinel")

    @current_app.on_event("startup")
    async def _startup() -> None:
        from app.db import init_db

        init_db()
        if "RUN_INITIAL_UPDATE" in os.environ:
            from app.db_entry_update import update_database

            await update_database()

    @current_app.get("/ping")
    async def _ping() -> str:
        return "pong"

    from .tasks import router as tasks_router

    current_app.include_router(tasks_router, prefix="/tasks")

    return current_app


app = create_app()
