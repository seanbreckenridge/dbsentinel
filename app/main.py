from typing import Callable
from fastapi import FastAPI, Response, Request


def create_app() -> FastAPI:
    from app.settings import settings

    current_app = FastAPI(title="dbsentinel")

    @current_app.on_event("startup")
    async def _startup() -> None:
        from app.db import init_db

        init_db()

    @current_app.get("/ping")
    async def _ping() -> str:
        return "pong"

    from .tasks import trouter as tasks_router
    from .summary import router as summary_router
    from .query import router as query_router

    current_app.include_router(tasks_router, prefix="/tasks")
    current_app.include_router(summary_router, prefix="/summary")
    current_app.include_router(query_router, prefix="/query")

    @current_app.middleware("http")
    async def _authenticate(request: Request, call_next: Callable) -> Response:
        if request.headers.get("Authorization") != settings.BEARER_SECRET:
            return Response(status_code=401, content="Unauthorized")
        return await call_next(request)  # type: ignore

    return current_app


app = create_app()
