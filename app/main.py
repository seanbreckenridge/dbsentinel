import tracemalloc
from typing import Callable

from fastapi import FastAPI, Response, Request, status, Query
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from mal_id.log import logger


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

    @current_app.get("/memory/start")
    async def _memory_start() -> str:
        tracemalloc.start()
        return "started"

    @current_app.get("/memory")
    async def _memory(count: int = Query(default=25)) -> list[str]:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        return list(map(str, top_stats[:count]))

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

    # https://github.com/tiangolo/fastapi/issues/3361#issuecomment-1002120988
    @current_app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> Response:
        exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
        logger.error(f"{request}: {exc_str}")
        content = {"status_code": 422, "message": exc_str}
        logger.warning(f"request body: {request.body()}")
        logger.error(exc, exc_info=True)
        return JSONResponse(
            content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    return current_app


app = create_app()
